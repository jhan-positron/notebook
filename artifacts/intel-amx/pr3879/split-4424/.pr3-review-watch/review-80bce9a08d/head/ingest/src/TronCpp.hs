{-# LANGUAGE LambdaCase #-}
{-# LANGUAGE NamedFieldPuns #-}
{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE PatternSynonyms #-}
{-# LANGUAGE RecordWildCards #-}

-- | Translation of Tron to C++.
-- |
-- | To process a Tron model, I need to generate the bits of C++ that
-- | the tron runtime system will hook into.  That consists of a packaging struct
-- | named for the model, with
-- | - struct `plugin_model` (?) for inserting into the LLM, holding weights
-- |   and configuration fields
-- |   - Need to know the types and sizes of the weights and the
-- |     configuration fields
-- | - Method `plugin_model::visit_named_tensors` for loading the model
-- |   from a safetensors file
-- | - struct `state` for inserting into the state
-- |   - Need to know how large the buffers are
-- | - struct `plugin_batch` for inserting into the minibatch
-- |   - Constructor(state, items, latches, ix)
-- |     - Insert string names for the channels
-- | - Method `plugin_batch::reset_channels(n_attn_workers, n_main_workers)`
-- |   - Maybe an accessor for the last channel, so the batch
-- |     destructor can `producer_barrier.next_phase` on it
-- | - Method `state::run` for the main thread; it also launches the
-- |   helper and attention workers and waits for them before returning,
-- |   per Note [Plugin-owned worker launch] in model.hpp. It does not wait
-- |   for matmul completion callbacks: each launch counts its callback on
-- |   the batch, whose destructor retires them, per
-- |   Note [Matrix callback lifetime] in common.hpp
-- | - Method `state::run_main_help` for the helpers
-- | - Method `state::run_attention_worker`, generated from the ordered
-- |   `AttentionStmt`s in the program
-- | - Method `state::resize` for resizing the buffers
-- |
-- | Semantically, this pass does the following work:
-- | - Interprets `Buffer`s as explicit fields in the `state` struct
-- | - Implements `Channel` guards by placing explicit code blocks
-- |   around uses of the protected buffers.
-- | - Resolves iteration spaces for the outer parallel loop and inner `For` loops (QBatchItems or Fin)
-- | - Parallelizes the outer loop using a thread assignment strategy
-- | - Lowers `For` loops as sequential C++ `for` loops
module TronCpp (process) where

import Control.Monad (join)
import Data.List qualified as List
import Data.List.NonEmpty qualified as NE
import Data.Map.Strict qualified as M
import Data.Maybe (catMaybes, fromMaybe, isJust, mapMaybe)
import Data.Set qualified as S
import Data.String (fromString)
import Data.Text qualified as T
import Prettyprinter qualified as PP
import Prelude hiding (read)

import Cpp
import LoadOp (LoadOp (..), loadOpKey)
import Name hiding (NameKind (Var))
import Ops qualified
import Provenance
  ( ProvenanceSet
  , provenanceTraceID
  , unTraceID
  )
import Size
  ( IterationSpaceF (..)
  , KnownDim (..)
  , SizeF (..)
  , SizeVarF (..)
  , TermF (..)
  , sizeToCppWith
  , pattern Static
  )
import TargetExecutor (TargetExecutor)
import TargetExecutor qualified
import Tron
import TronCheck qualified
import TypedFx
  ( AttentionType (..)
  , BinaryOp (..)
  , InputTokenRemapping (..)
  , LogitsMunge (..)
  , validateInputTokenRemappings
  )
import Utils (expectJust, panic)

-- Note [C++ codegen code style]
-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
--
-- The style for creating C++ syntax in this file has two desiderata:
--
-- 1. Avoid creating syntax with string concatenation (++); add new
--    constructors in Cpp.hs to fill in the model of the C++ AST as
--    needed.  This localizes responsibility for getting syntactic
--    composition correct.
--
--    Bad: LitStmt $ "q_batch->" ++ show name ++ ".start_reading_at(" ++ show arg ++ ");"
--
--    Good: ExprStmt $
--      MethodCall (MemberAccess "q_batch" (asCpp name)) "start_reading_at" [arg]
--
-- 2. Avoid using Cpp.hs AST constructors for static subexpressions
--    or statements that have no interpolation, because C++ source
--    is much easier to read.
--
--    Bad: Declare
--           (PointerType (LiteralType "plugin_batch"))
--           (Var "q_batch")
--           (AddrOf
--             (MemberAccess
--               (Index (Var "q_batches") (LiteralExpr (IntLit 0)))
--               "plugin_batch"))
--
--    Good: LitStmt "plugin_batch* q_batch = &q_batches[0]->plugin_batch;"

-- | Create a derived C++ name by appending a suffix to an existing name.
derivedCppName :: Name k -> String -> Name Cpp
derivedCppName name suffix = fromString (show name ++ "_" ++ suffix)

-- | Sanitize a model name for use as a C++ identifier.
-- Replaces hyphens with underscores since C++ identifiers cannot contain hyphens.
-- Panics if the result is still not a valid C++ identifier: the name is
-- spliced directly into the generated C++ as a struct name and in raw
-- template strings, so a malformed name would produce malformed C++
-- (or worse, allow C++ injection via characters like newline or @;@).
sanitizeCppIdent :: String -> String
sanitizeCppIdent name
  | isValidCppIdent sanitized = sanitized
  | otherwise =
      error $
        "TronCpp.process: model name "
          ++ show name
          ++ " is not a valid C++ identifier"
          ++ ( if sanitized == name
                 then ""
                 else " (sanitized to " ++ show sanitized ++ ")"
             )
 where
  sanitized = map (\c -> if c == '-' then '_' else c) name

-- | Compute a trace comment suffix from a provenance set.
-- Returns empty string when provenance is empty; otherwise
-- returns @" // [T:\<id\>]"@ for embedding in generated C++.
traceComment :: ProvenanceSet -> String
traceComment prov
  | S.null prov = ""
  | otherwise =
      " // [T:"
        ++ T.unpack (unTraceID (provenanceTraceID prov))
        ++ "]"

process :: String -> TargetExecutor -> Module -> CppFile
process name target m =
  ensureValid $
    CppFile $
      join
        [
          [ LiteralD "#pragma once\n"
          , IncludeD $ IncludeLocal "common/indexed.hpp"
          , IncludeD $ IncludeLocal "common/json.hpp"
          , IncludeD $ IncludeLocal "tron/hardware/placer.hpp"
          , IncludeD $ IncludeLocal "tron/kernels/rope.hpp"
          , IncludeD $ IncludeLocal "tron/kernels/strided_copy.hpp"
          , IncludeD $ IncludeLocal "tron/kernels/topk.hpp"
          , IncludeD $ IncludeLocal "tron/kernels/clamp.hpp"
          , IncludeD $ IncludeLocal "tron/models/moe_router_id.hpp"
          ]
        , permutedIncludes
        , cacheIncludes
        , [IncludeD $ IncludeLocal "tron/tensor/itensor.hpp"]
        , hostMatrixIncludes
        , [IncludeD $ IncludeLocal "common/perfetto.hpp"]
        ,
          [ IncludeD $ IncludeLocal "tron/models/common.hpp"
          , IncludeD $ IncludeLocal "tron/models/kernel_strategy.hpp"
          , IncludeD $ IncludeLocal "tron/models/mixture_of_experts.hpp"
          , IncludeD $ IncludeLocal "tron/models/model.hpp"
          , IncludeD $ IncludeLocal "tron/models/self_attention.hpp"
          , LiteralD "\nnamespace tron {\n"
          ]
        , map LiteralD $ literalCpps m
        , -- Generate the implementation template (top-level) and the
          -- wrapper struct with type alias.  The static_assert enforces
          -- that the chosen executor matches the mode this plugin was
          -- ingested for; the message names the flag to flip when the
          -- pairing is wrong.

          [ StructDefD $ modelStruct (cppName ++ "_impl") target m
          , StructDefD $
              StructDef
                (fromString cppName)
                ["llm_executor exe"]
                [ LiteralDef staticAssertExecutor
                , LiteralDef $ "using plugin_model = " ++ cppName ++ "_impl<exe>;"
                ]
          , LiteralD "\n} // namespace tron\n"
          ]
        ]
 where
  ensureValid result = TronCheck.assertValidModule "TronCpp.process" m `seq` result
  cppName = sanitizeCppIdent name
  permutedIncludes
    | TargetExecutor.isPermuted target =
        [ IncludeD $ IncludeLocal "tron/hardware/permuted.hpp"
        , IncludeD $ IncludeLocal "tron/kernels/permutation.hpp"
        ]
    | otherwise = []
  hostMatrixIncludes
    | hasHostMatrixTensors m =
        [IncludeD $ IncludeLocal "tron/tensor/weight_matrix.hpp"]
    | otherwise = []
  cacheIncludes = case attentionCacheTopology m of
    UniformAttentionCache{} -> []
    HeterogeneousAttentionCache _ ->
      [IncludeD $ IncludeLocal "tron/models/heterogeneous_kv_cache.hpp"]
  staticAssertExecutor = case target of
    TargetExecutor.Permuted ->
      "static_assert(exe::permuted, \"This plugin was ingested with --target-executor permuted and requires a perm_tp{1,2,4} executor; re-ingest with --target-executor plain to use a tp{1,2,4} executor.\");"
    TargetExecutor.Plain ->
      "static_assert(!exe::permuted, \"This plugin was ingested with --target-executor plain and requires a tp{1,2,4} executor; re-ingest with --target-executor permuted to use a perm_tp{1,2,4} executor.\");"

modelStruct :: String -> TargetExecutor -> Module -> StructDef
modelStruct name target m@Module{modDecls = env, mainKernel = run, inputTokenRemappings} =
  StructDef (fromString name) ["llm_executor exe"] $
    [ LiteralDef
        "template <size_t M, size_t N> using dtensor_t = typename exe::template dtensor_t<M, N>;"
    , LiteralDef
        "template <size_t M, size_t N> using expert_dtensor_t = typename exe::template expert_dtensor_t<M, N>;"
    , LiteralDef
        "template <size_t d, size_t... ds> using btensor_t = typename exe::template btensor_t<d, ds...>;"
    , LiteralDef
        "template <size_t d, size_t... ds> using itensor_t = tron::itensor<d, ds...>;"
    ]
      ++ map FieldDef (configFields m)
      ++ cacheComponents m
      ++ [ LiteralDef
             "static constexpr bool is_host = std::is_same_v<dtensor_t<dim, dim>, tensor<dim, dim>>;"
         , LiteralDef "static constexpr bool wcls_is_compensated = !is_host;"
         , LiteralDef "static constexpr bool attn_softcapping = false;"
         , LiteralDef "static constexpr bool is_eagle = false;"
         , LiteralDef "static constexpr bool force_hw_attn = true;"
         , -- Declare the MoE shape so the framework can size its
           -- routing state and the codegen-emitted
           -- `expert_stats_.record_router(...)` call compiles. See
           -- Note [MoE Expert Routing Stats] in
           -- h/tron/models/expert_stats.hpp.
           FieldDef $
             StaticConstexprField "bool" "moe" (LiteralExpr (BoolLit (not (null routings))))
         , FieldDef $
             StaticConstexprField
               "size_t"
               "n_routed_experts"
               (LiteralExpr (IntLit (fromIntegral nRoutedExperts)))
         , FieldDef $
             StaticConstexprField
               "size_t"
               "n_moe_routers"
               (LiteralExpr (IntLit (fromIntegral nMoeRouters)))
         , -- Keep top-k values in generated routing-site order, matching the
           -- explicit MoeRouteStmt router ID and the expert-load profile rows.
           FieldDef $
             InlineStaticConstField
               routingTopKType
               "expert_routing_top_k_by_router"
               (BraceInit routingTopKStorageType routingTopKValues)
         , FieldDef $
             StaticConstexprField
               "bool"
               "permuted"
               (LiteralExpr (BoolLit (TargetExecutor.isPermuted target)))
         , LiteralDef "static constexpr int max_minibatches = 1;"
         , LiteralDef "static constexpr size_t max_minibatch_size = 1024;"
         , FieldDef $
             StaticConstexprField
               "size_t"
               "n_attention_ops"
               (LiteralExpr (IntLit (fromIntegral (length (attentionOperations run)))))
         , FieldDef $ attentionKernelRegistryField run
         , FieldDef $ attentionSinkRegistryField run
         , FieldDef $ attentionOperationDescriptorsField run
         , LiteralDef
             "static_assert(tron::valid_attention_configuration(attention_kernels, attention_operations, cache_t::kv_slot_specs, attention_sink_specs));"
         , LiteralDef
             "static constexpr size_t active_attention_operation_count(size_t) noexcept { return n_attention_ops; }"
         , LiteralDef "struct plugin_batch;" -- Forward declaration for plugin_batch
         , MethodDef $ inputTokenRemapMethod inputTokenRemappings
         ]
      ++ map FieldDef (tensorFields m)
      ++ map FieldDef (permutationFields m)
      ++ [ ConstructorDef $ modelConstructor name m
         , LiteralDef "void cache_weights(std::string) noexcept { }"
         , finalizeWeightsDef m
         , MethodDef $ visitNamedTensorsMethod m
         , MethodDef $ attentionSinkAccessor run
         , NestedStructDef $ stateStruct name m
         , NestedStructDef $ batchPluginStruct name m
         ]
 where
  routings = getMoeRoutings env
  nMoeRouters = length [() | MoeRouteStmt{} <- mainKernel m]
  -- All routings in a model share the same expert count today; pick
  -- it off the first one (0 for non-MoE plugins).
  nRoutedExperts = case routings of
    [] -> 0
    ((_, info) : _) -> moeRoutingNumExperts info
  routingTopKs = mapMaybe routingTopK run
  routingTopK (MoeRouteStmt routingName _ _ _) =
    Just $ moeRoutingTopK $ readDecl routingName env
  routingTopK _ = Nothing
  routingTopKType =
    TemplateType
      "indexed_vector"
      [LiteralType "moe_router_id", LiteralType "size_t"]
  routingTopKStorageType =
    TemplateType "std::vector" [LiteralType "size_t"]
  routingTopKValues =
    map (LiteralExpr . IntLit . fromIntegral) routingTopKs

-- | Whether any tensor is in the 'HostMatrix' memory space.
-- See Note [HostMatrix weights] in Tron.hs.
hasHostMatrixTensors :: Module -> Bool
hasHostMatrixTensors =
  any ((== HostMatrix) . memorySpace . snd) . getTensors . modDecls

-- | Whether any host statement runs on the aligned lane domain.
-- See Note [Aligned lane domain].
hasAlignedLanes :: Module -> Bool
hasAlignedLanes Module{modDecls = env, mainKernel = run} =
  any ((== AlignedLanes) . kernelLanes . snd) (getKernels env)
    || not (null [() | MoeBlendStmt _ _ _ _ _ AlignedLanes _ <- run])

-- | The @finalize_weights()@ method. It warns once if any 'HostMatrix' tensor
-- has FP32 storage. Without a 'HostMatrix' tensor its body is empty.
-- See Note [HostMatrix weights] in Tron.hs.
finalizeWeightsDef :: Module -> StructComponent
finalizeWeightsDef m
  | null hostMatrices = LiteralDef "void finalize_weights() noexcept { }"
  | otherwise =
      MethodDef $
        Method "void" "finalize_weights" [] [MethodNoexcept] $
          Block $
            [ Cpp.Comment "See Note [HostMatrix weights] in ingest/src/Tron.hs."
            , Declare "fp32_storage_log" storageLog Nothing
            ]
              ++ map addMatrix hostMatrices
              ++ [ExprStmt $ MethodCall (Var storageLog) "report" []]
 where
  hostMatrices =
    [ (name, loadOp info)
    | (name, info) <- getTensors (modDecls m)
    , memorySpace info == HostMatrix
    ]
  storageLog = "fp32_storage"
  addMatrix (name, loadOp) =
    ExprStmt $
      MethodCall
        (Var storageLog)
        "add"
        [ LiteralExpr $ StringLit $ mungeSafetensorsKey $ loadOpKey loadOp
        , Var $ asCpp name
        ]

inputTokenRemapMethod :: [InputTokenRemapping] -> Method
inputTokenRemapMethod remappings = case validateInputTokenRemappings Nothing remappings of
  Left err -> error $ "TronCpp.inputTokenRemapMethod: " <> err
  Right () ->
    Method
      (LiteralType "token_t")
      "remap_input_token"
      [ParamLit "token_t token"]
      [MethodConst, MethodNoexcept]
      (Block [ReturnStmt $ Just remapped])
 where
  remapped = foldr applyRemapping (Var "token") remappings
  applyRemapping InputTokenRemapping{..} =
    TernaryOp
      (BinOp Eq (Var "token") (LiteralExpr $ IntLit inputTokenSource))
      (LiteralExpr $ IntLit inputTokenTarget)

-- | The statically ordered attention-worker schedule.
attentionOperations :: [Tron.Statement] -> [AttentionOperation]
attentionOperations = mapMaybe $ \case
  AttentionStmt attention -> Just attention
  _ -> Nothing

attentionOperationsById :: [Tron.Statement] -> M.Map AttentionOpId AttentionOperation
attentionOperationsById =
  M.fromList . map (\stmt -> (attentionOpId stmt, stmt)) . attentionOperations

-- | Entries are embedded in operations during lowering so the IR stays local,
-- then deduplicated here into the plugin-owned registry.
attentionKernels :: [Tron.Statement] -> [AttentionKernelSpec]
attentionKernels run = M.elems $ M.fromList entries
 where
  entries =
    [ (attentionKernelId spec, spec)
    | operation <- attentionOperations run
    , let spec = attentionKernel operation
    ]

attentionGeometryExpr :: AttentionGeometry -> Cpp.Expr
attentionGeometryExpr AttentionGeometry{..} =
  BraceInit
    "tron::attention_geometry"
    [ attentionQueryHeads
    , BraceInit "tron::kv_geometry" [attentionKvHeads, attentionHeadSize]
    ]

attentionKernelExpr :: AttentionKernelSpec -> Cpp.Expr
attentionKernelExpr AttentionKernelSpec{..} =
  BraceInit
    "tron::attention_kernel_spec"
    [ FunCall
        "tron::attention_kernel_id"
        [LiteralExpr $ IntLit $ unAttentionKernelId attentionKernelId]
    , attentionGeometryExpr attentionGeometry
    ]

attentionCapabilityExpr :: AttentionHardwareCapability -> Cpp.Expr
attentionCapabilityExpr SoftwareAttentionOnly =
  ExprLit "tron::attention_hardware_capability::software_only"
attentionCapabilityExpr KvSlotHardwareAttentionCandidate =
  ExprLit "tron::attention_hardware_capability::kv_slot_candidate"

-- | Unique sink tensors in first-use order. The operation supplies the
-- query-head count embedded in the corresponding registry entry.
attentionSinkEntries :: [Tron.Statement] -> [(Name ('Tron 'Tensor), AttentionOperation)]
attentionSinkEntries run =
  [ (sink, operationFor sink)
  | sink <- List.nub sinks
  ]
 where
  operations = attentionOperations run
  sinks = mapMaybe (attentionSinks . attentionConfig) operations
  operationFor sink =
    expectJust
      ( "TronCpp.attentionSinkEntries: sink weight has no attention operation:"
          PP.<+> PP.pretty sink
      )
      ( List.find
          ((== Just sink) . attentionSinks . attentionConfig)
          operations
      )

attentionSinkId
  :: [(Name ('Tron 'Tensor), AttentionOperation)] -> Name ('Tron 'Tensor) -> Integer
attentionSinkId entries sink =
  fromIntegral $
    expectJust
      ( "TronCpp.attentionSinkId: sink weight is not among the sink entries:"
          PP.<+> PP.pretty sink
      )
      (List.elemIndex sink (map fst entries))

attentionConfigExpr
  :: [(Name ('Tron 'Tensor), AttentionOperation)] -> AttentionOperation -> Cpp.Expr
attentionConfigExpr sinkEntries operation =
  BraceInit
    "tron::attention_operation_config"
    [ case attentionType config of
        FullCausal -> ExprLit "std::nullopt"
        SlidingWindow window -> LiteralExpr $ IntLit window
    , case attentionSinks config of
        Nothing -> ExprLit "std::nullopt"
        Just sink ->
          FunCall
            "tron::attention_sink_id"
            [LiteralExpr $ IntLit $ attentionSinkId sinkEntries sink]
    , LiteralExpr $ FloatLit $ realToFrac $ attentionScale config
    ]
 where
  config = attentionConfig operation

attentionOperationDescriptorExpr
  :: [(Name ('Tron 'Tensor), AttentionOperation)] -> AttentionOperation -> Cpp.Expr
attentionOperationDescriptorExpr sinkEntries operation =
  BraceInit
    "tron::attention_operation_descriptor"
    [ attentionBindingExpr operation
    , FunCall
        "tron::attention_kernel_id"
        [ LiteralExpr $
            IntLit $
              unAttentionKernelId $
                attentionKernelId $
                  attentionKernel operation
        ]
    , attentionCapabilityExpr $ attentionHardwareCapability operation
    , LiteralExpr $ BoolLit $ isJust $ attentionKvWrite operation
    , attentionConfigExpr sinkEntries operation
    ]

attentionKernelRegistryField :: [Tron.Statement] -> Field
attentionKernelRegistryField run =
  StaticConstexprField "auto" "attention_kernels" $
    BraceInit registryType (map attentionKernelExpr kernels)
 where
  kernels = attentionKernels run
  registryType =
    TemplateType
      "std::array"
      [ LiteralType "tron::attention_kernel_spec"
      , ExprType $ LiteralExpr $ IntLit $ fromIntegral $ length kernels
      ]

attentionOperationDescriptorsField :: [Tron.Statement] -> Field
attentionOperationDescriptorsField run =
  StaticConstexprField "auto" "attention_operations" $
    BraceInit
      descriptorType
      (map (attentionOperationDescriptorExpr sinkEntries) operations)
 where
  operations = attentionOperations run
  sinkEntries = attentionSinkEntries run
  descriptorType =
    TemplateType
      "std::array"
      [ LiteralType "tron::attention_operation_descriptor"
      , ExprType $ LiteralExpr $ IntLit $ fromIntegral $ length operations
      ]

-- | Persistent retention for one KV slot. An unused declared slot remains
-- resident. A shared slot also remains resident when any consumer uses
-- full-history attention; otherwise its widest sliding window is sufficient
-- for every consumer.
attentionSlotRetention :: [AttentionOperation] -> KvSlotId -> AttentionType
attentionSlotRetention operations slot =
  case map (attentionType . attentionConfig) consumers of
    [] -> FullCausal
    first : rest -> List.foldl' widestRetention first rest
 where
  consumers = filter ((== slot) . attentionKvSlot) operations
  widestRetention FullCausal _ = FullCausal
  widestRetention (SlidingWindow _) FullCausal = FullCausal
  widestRetention (SlidingWindow left) (SlidingWindow right) =
    SlidingWindow $ max left right

attentionSlotRetentionExpr :: [AttentionOperation] -> KvSlotId -> Cpp.Expr
attentionSlotRetentionExpr operations slot =
  case attentionSlotRetention operations slot of
    FullCausal -> FunCall "tron::kv_slot_retention::full_history" []
    SlidingWindow window ->
      FunCall
        "tron::kv_slot_retention::sliding_window"
        [LiteralExpr $ IntLit window]

attentionUsesSlidingWindow :: AttentionOperation -> Bool
attentionUsesSlidingWindow operation =
  case attentionType $ attentionConfig operation of
    FullCausal -> False
    SlidingWindow _ -> True

attentionSinkRegistryField :: [Tron.Statement] -> Field
attentionSinkRegistryField run =
  StaticConstexprField "auto" "attention_sink_specs" $
    BraceInit registryType $
      map sinkSpecExpr entries
 where
  entries = attentionSinkEntries run
  registryType =
    TemplateType
      "std::array"
      [ LiteralType "tron::attention_sink_spec"
      , ExprType $ LiteralExpr $ IntLit $ fromIntegral $ length entries
      ]
  sinkSpecExpr (sink, operation) =
    BraceInit
      "tron::attention_sink_spec"
      [ FunCall
          "tron::attention_sink_id"
          [LiteralExpr $ IntLit $ attentionSinkId entries sink]
      , attentionQueryHeads $ attentionGeometry $ attentionKernel operation
      ]

-- | Resolve a generated sink ID to the existing typed tensor field. Generic
-- tensor visitation loads that field exactly once; this accessor adds no
-- storage and is called only while model state binds operation configuration.
attentionSinkAccessor :: [Tron.Statement] -> Method
attentionSinkAccessor run =
  Method
    sinkSpanType
    "attention_sink"
    [ParamLit "tron::attention_sink_id id"]
    [MethodConst, MethodNoexcept]
    ( Block $
        zipWith sinkCase [0 :: Integer ..] entries
          ++ [ invalidSinkId
             , ReturnStmt $ Just $ BraceInit sinkSpanType []
             ]
    )
 where
  entries = attentionSinkEntries run
  sinkSpanType = TemplateType "std::span" [ConstType "float"]

  sinkCase sinkId (sink, _) =
    IfStmt
      ( BinOp
          Eq
          (FieldRef (Var "id") "i")
          (LiteralExpr $ IntLit sinkId)
      )
      ( Block
          [ ReturnStmt $
              Just $
                BraceInit
                  sinkSpanType
                  [FieldRef (Var $ asCpp sink) "data"]
          ]
      )
      Nothing

  invalidSinkId =
    ExprStmt $
      FunCall
        "TRON_ASSERT"
        [ LiteralExpr $ BoolLit False
        , LiteralExpr $ StringLit "invalid attention sink ID {}"
        , FieldRef (Var "id") "i"
        ]

-- | Declare plugin-owned persistent slot topology independently of operation
-- descriptors. Uniform schemas retain the book alias; explicit schemas become
-- the heterogeneous cache's value template argument.
cacheComponents :: Module -> [StructComponent]
cacheComponents m = case attentionCacheTopology m of
  UniformAttentionCache slotCount kvHeads headSize ->
    retentionField slotCount
      ++ [ UsingAliasDef
             "cache_t"
             ( TemplateType
                 "tron::uniform_kv_cache"
                 ( [ ExprType slotCount
                   , ExprType $
                       BraceInit
                         "tron::kv_geometry"
                         [kvHeads, headSize]
                   , ExprType cacheXBytes
                   ]
                     ++ [ExprType $ Var "cache_slot_retentions" | hasSlidingWindow]
                 )
             )
         ]
  HeterogeneousAttentionCache slots ->
    [ FieldDef $
        StaticConstexprField "auto" "cache_slot_specs" $
          BraceInit
            ( TemplateType
                "std::array"
                [ LiteralType "tron::kv_slot_spec"
                , ExprType $ LiteralExpr $ IntLit $ fromIntegral $ length slots
                ]
            )
            (map cacheSlotSpecExpr slots)
    , UsingAliasDef
        "cache_t"
        ( TemplateType
            "tron::heterogeneous_kv_cache"
            [ExprType $ Var "cache_slot_specs", ExprType cacheXBytes]
        )
    ]
 where
  operations = attentionOperations $ mainKernel m
  hasSlidingWindow = any attentionUsesSlidingWindow operations
  retentionField slotCount =
    [ FieldDef $
        StaticConstexprField "auto" "cache_slot_retentions" $
          Apply
            ( Lambda [] [] $
                Block $
                  [ Declare
                      "auto"
                      "retentions"
                      ( Just $
                          TemplateFunCall
                            "tron::full_history_kv_slot_retentions"
                            [ExprType slotCount]
                            []
                      )
                  ]
                    ++ [ Assignment
                           ( Index
                               "retentions"
                               (LiteralExpr $ IntLit $ unKvSlotId slot)
                           )
                           (attentionSlotRetentionExpr operations slot)
                       | slot <- uniformSlots
                       , attentionSlotRetention operations slot /= FullCausal
                       ]
                    ++ [ReturnStmt $ Just "retentions"]
            )
            []
    | hasSlidingWindow
    ]
  uniformSlots = List.sort $ List.nub $ map attentionKvSlot operations
  cacheXBytes =
    ExprLit "dim * sizeof(typename btensor_t<dim>::scalar)"
  cacheSlotSpecExpr AttentionCacheSlotSpec{..} =
    BraceInit
      "tron::kv_slot_spec"
      [ BraceInit
          "tron::kv_geometry"
          [attentionCacheSlotKvHeads, attentionCacheSlotHeadSize]
      , attentionSlotRetentionExpr operations attentionCacheSlotId
      ]

-- | Extracts config fields for the top-level 'model' struct.
configFields :: Module -> [Field]
configFields m = map getConfigField (getConfigs (modDecls m))
 where
  getConfigField :: (Name ('Tron 'Config), ConfigInfo) -> Field
  getConfigField
    (name, ConfigInfo{configType = ty, configInitialization = ConstexprValue value}) =
      StaticConstexprField ty (asCpp name) value
  getConfigField (name, ConfigInfo{configType = ty}) = Field ty (asCpp name)

-- | Extracts tensor fields for the top-level 'model' struct.
-- Weight tensors use non-initializing constructors to avoid
-- unnecessary zero-initialization of unused layers.
tensorFields :: Module -> [Field]
tensorFields m = map getTensorField (getTensors (modDecls m))
 where
  getTensorField :: (Name ('Tron 'Tensor), TensorInfo) -> Field
  getTensorField (name, ti) =
    FieldBraceInit (tensorType ti) (asCpp name) (ExprLit "uninitialized")

-- | Per-weight @permutation\<N\>@ fields for the model struct, one for
-- each 'PermutationInfo' declared in the env.
permutationFields :: Module -> [Field]
permutationFields m =
  [ Field (TemplateType "permutation" [ExprType (permArity info)]) (asCpp name)
  | (name, info) <- getPermutations (modDecls m)
  ]

-- | Generate C++ type for a tensor given its shape and memory space.
tensorTypeFromShapeAndSpace :: [Expr] -> MemorySpace -> Type
tensorTypeFromShapeAndSpace shape memSpace = case memSpace of
  Host -> TemplateType "tensor" $ map ExprType shape
  HostMatrix -> case shape of
    [rows, cols] -> TemplateType "weight_matrix" [ExprType rows, ExprType cols]
    _ -> error $ "HostMatrix tensors must be rank 2, got shape " ++ show shape
  Device -> TemplateType "dtensor_t" $ map ExprType shape
  Compensated -> TemplateType "dtensor_t" $ map ExprType $ widen shape
 where
  widen :: [Expr] -> [Expr]
  widen [output, input] = [output, TernaryOp (Var "wcls_is_compensated") (BinOp Add input input) input]
  widen s =
    error $
      "Trying to make a compensated tensor with the wrong number of dimensions: "
        ++ show s

-- | C++ type for a per-expert weight tensor. Uses `expert_dtensor_t` so
-- expert weights stay TP1 (single device) even under tpN executors.
-- See Note [Expert matmuls].
expertTensorTypeFromShapeAndSpace :: [Expr] -> MemorySpace -> Type
expertTensorTypeFromShapeAndSpace shape memSpace = case memSpace of
  Host -> TemplateType "tensor" $ map ExprType shape
  HostMatrix -> error "HostMatrix expert tensors are not supported"
  Device -> TemplateType "expert_dtensor_t" $ map ExprType shape
  Compensated ->
    error "Compensated expert tensors are not supported"

tensorType :: TensorInfo -> Type
tensorType TensorInfo{shape, loadOp, memorySpace = memSpace} =
  case loadOp of
    LoadSafetensors{} -> tensorTypeFromShapeAndSpace shape memSpace
    LoadExpertSafetensors nExperts _ ->
      -- For MoE expert weights: expert_weights<expert_dtensor_t<M, N>, NumExperts>
      -- Strip the expert dimension (first) from the 3D shape. `expert_dtensor_t`
      -- forces single-device placement per expert even under tpN executors.
      TemplateType
        "expert_weights"
        [ expertTensorTypeFromShapeAndSpace (drop 1 shape) memSpace
        , ExprType (LiteralExpr (IntLit (fromIntegral nExperts)))
        ]

-- Constructor for the model struct with configuration parameters
modelConstructor :: String -> Module -> Constructor
modelConstructor implName m@Module{} =
  Constructor (fromString implName) params initializers body
 where
  params =
    [ ParamLit "json config"
    , ParamLit "tron_maybe_unused int max_layers = -1"
    ]
  initializers = configInitializers m
  body =
    Block
      [ runtimeLayerTruncationAssert "max_layers"
      , descActEnforce
      ]
  -- Refuse a checkpoint whose GPTQ /quantization_config/desc_act
  -- doesn't match the mode this plugin was ingested for. With the
  -- 4-arg form, "required" tracks "expect": when permuted=true the
  -- field must be present *and* equal to true; when permuted=false
  -- the field may be absent (non-quantized models) but if present
  -- must equal false. Catches mode mismatches at load time with a
  -- spdlog::info trace.
  descActEnforce =
    LitStmt
      "json_enforce(config, \"/quantization_config/desc_act\"_json_pointer, permuted, permuted);"

configInitializers :: Module -> [Cpp.Initializer]
configInitializers m = mapMaybe generate_config_initializer $ getConfigs $ modDecls m
 where
  generate_config_initializer :: (Name ('Tron 'Config), ConfigInfo) -> Maybe Initializer
  generate_config_initializer (_, ConfigInfo{configInitialization = ConstexprValue _}) =
    Nothing
  generate_config_initializer (name, ConfigInfo{configInitialization = FromCtor args}) =
    Just $ Initializer (asCpp name) args

-- | Identity of an expert weight tensor within one MoE router.
newtype ExpertTensorId = ExpertTensorId {unExpertTensorId :: Integer}
  deriving (Eq, Ord, Show)

-- | One logical router's routing field and its expert matmul operations,
-- ordered by 'ExpertMatmulId'. Argument k of the router's generated
-- @make_expert_matmul_schedule@ call and @jobs_for(expert_matmul_id{k})@ both
-- come from that ID, which 'TronCheck.checkMoeRouters' requires to be dense in
-- operation order.
data MoeRouterInfo = MoeRouterInfo
  { routerRouting :: Name ('Tron 'MoeRouting)
  , routerMatmuls :: [MoeMatmulOperation]
  }

moeRouters :: [Tron.Statement] -> [(MoeRouterId, MoeRouterInfo)]
moeRouters run =
  [ ( routerId
    , MoeRouterInfo
        { routerRouting = routing
        , routerMatmuls = matmulsOf routerId
        }
    )
  | MoeRouteStmt routing _ routerId _ <- run
  ]
 where
  matmulsOf :: MoeRouterId -> [MoeMatmulOperation]
  matmulsOf routerId =
    List.sortOn moeMatmulId $
      [ op
      | MoeMatmulPrepareAndLaunchStmt op <- run
      , moeMatmulRouterId op == routerId
      ]

-- | The state field holding a router's expert matmul schedule.
moeScheduleName :: MoeRouterId -> Name Cpp
moeScheduleName (MoeRouterId r) = fromString $ "moe_router_" ++ show r ++ "_schedule"

-- | Assign dense, per-router tensor IDs in first semantic matmul-use order.
expertTensorPlacementIds
  :: [Tron.Statement]
  -> M.Map (MoeRouterId, Name ('Tron 'Tensor)) ExpertTensorId
expertTensorPlacementIds run =
  M.fromList
    [ ((routerId, tensor), ExpertTensorId tensorOrdinal)
    | (routerId, info) <- moeRouters run
    , (tensorOrdinal, tensor) <-
        zip [0 ..] $ List.nub $ map moeMatmulTensor $ routerMatmuls info
    ]

-- | Wraps each matmul-input weight's safetensors load in
-- @permuted_tensor(perm, weight)@ when the tensor has a paired
-- 'Permutation' (i.e. the BulkLoopy pipeline emitted an 'L.Load2' for
-- that weight, which 'LoopyTron' translated into a 'PermutationInfo'
-- and attached to the tensor's 'tensorPermutation' field).  The
-- capture writes load-time @g_idx@ into the sibling permutation field
-- declared by 'permutationFields'.
visitNamedTensorsMethod :: Module -> Method
visitNamedTensorsMethod Module{modDecls = env, mainKernel = run} =
  Method "void" "visit_named_tensors" params [] body
 where
  params =
    [ ParamLit "const auto& visit"
    , ParamLit "tron_maybe_unused int max_layers = -1"
    , ParamLit "tron_maybe_unused bool tie_word_embeddings = false"
    ]
  -- The boolean parameter is kept for the common model.hpp
  -- visit_named_tensors call signature. Generated plugins ignore it;
  -- the frontend resolves tied heads to a concrete key at export time.
  body = Block $ map visit_tensor $ getTensors env

  -- Render the single safetensors key supplied by 'LoadOp'.
  safetensorsKeyExpr :: LoadOp -> Cpp.Expr
  safetensorsKeyExpr loadOp =
    LiteralExpr (StringLit (mungeSafetensorsKey (loadOpKey loadOp)))

  visit_tensor :: (Name ('Tron 'Tensor), TensorInfo) -> Cpp.Statement
  visit_tensor
    ( name
      , TensorInfo
          { loadOp
          , memorySpace = memSpace
          , tensorPlacementKind = kind
          , tensorPermutation = perm
          }
      ) =
      case loadOp of
        LoadSafetensors{} -> visit_safetensors_tensor name loadOp kind memSpace perm
        LoadExpertSafetensors nExperts template ->
          visit_expert_tensor
            name
            nExperts
            template
            perm
            kind

  -- N.B. expert weights are (so far) never compensated.
  --
  -- The compensated weight is the LM head (wcls); the frontend maps a tied
  -- head to its input embedding key (see 'safetensorsKeyExpr').
  visit_safetensors_tensor
    :: Name ('Tron 'Tensor)
    -> LoadOp
    -> TensorPlacementKind
    -> MemorySpace
    -> Maybe (Name ('Tron 'Permutation))
    -> Cpp.Statement
  visit_safetensors_tensor name loadOp kind Compensated _ =
    IfConstexprStmt
      (Var "wcls_is_compensated")
      ( Block
          [ Declare
              (LiteralType "auto")
              (fromString "e")
              (Just $ FunCall (NamedFun (fromString "tron::compensated_tensor")) [Var $ asCpp name])
          , visitLoadTarget loadOp kind (Var $ fromString "e")
          ]
      )
      ( Just $
          Block
            [visitLoadTarget loadOp kind (Var $ asCpp name)]
      )
  -- A dense-matmul weight with a paired perm: wrap in 'permuted_tensor'.
  visit_safetensors_tensor name loadOp kind _ (Just permName) =
    Block
      [ Declare
          (LiteralType "auto")
          wrapName
          ( Just $
              FunCall
                (NamedFun (fromString "tron::permuted_tensor"))
                [Var $ asCpp permName, Var $ asCpp name]
          )
      , visitLoadTarget loadOp kind (Var wrapName)
      ]
   where
    wrapName = derivedCppName name "permuted_view"
  visit_safetensors_tensor name loadOp kind _ Nothing =
    visitLoadTarget loadOp kind (Var $ asCpp name)

  visitLoadTarget :: LoadOp -> TensorPlacementKind -> Expr -> Cpp.Statement
  visitLoadTarget loadOp kind target =
    ExprStmt $
      FunCall
        "visit"
        [ target
        , case kind of
            OrdinaryTensor -> ordinaryTensorPlacementRequest name
            AttentionKeyProjectionTensor -> attentionKeyProjectionTensorPlacementRequest name
            AttentionValueProjectionTensor -> attentionValueProjectionTensorPlacementRequest name
            MoeRouterTensor -> moeRouterTensorPlacementRequest name
            MoeMatmulWeightTensor{} ->
              panic
                "TronCpp.visit_tensor: MoeMatmulWeightTensor requires LoadExpertSafetensors"
        ]
   where
    name = safetensorsKeyExpr loadOp

  visit_expert_tensor
    :: Name ('Tron 'Tensor)
    -> Int
    -> String
    -> Maybe (Name ('Tron 'Permutation))
    -> TensorPlacementKind
    -> Cpp.Statement
  visit_expert_tensor _name _nExperts _template (Just _) _ =
    -- A paired perm on an expert tensor isn't currently emitted by any
    -- frontend (BulkLoopy panics on rank-3 eligible weights).  Supporting
    -- it would also require 'permutationFields' to emit an
    -- expert-indexed container rather than a single 'permutation<N>';
    -- without that, indexing 'model.<perm>[expert_id(e)]' would produce
    -- C++ that fails to compile.  Fail loud here rather than emit it.
    panic
      "TronCpp.visit_tensor: paired permutation on LoadExpertSafetensors is not supported yet"
  visit_expert_tensor name nExperts template Nothing kind =
    ForStmt
      (Declare (LiteralType "size_t") "e" (Just (LiteralExpr (IntLit 0))))
      (BinOp Lt (Var "e") (LiteralExpr (IntLit (fromIntegral nExperts))))
      (IncAssignment (Var "e") Add (LiteralExpr (IntLit 1)))
      $ Block
        [ ExprStmt $
            FunCall
              "visit"
              [ Index (Var $ asCpp name) (FunCall "expert_id" [Var "e"])
              , case kind of
                  OrdinaryTensor -> ordinaryTensorPlacementRequest formattedName
                  AttentionKeyProjectionTensor -> attentionKeyProjectionTensorPlacementRequest formattedName
                  AttentionValueProjectionTensor -> attentionValueProjectionTensorPlacementRequest formattedName
                  MoeRouterTensor -> moeRouterTensorPlacementRequest formattedName
                  MoeMatmulWeightTensor routerId ->
                    moeMatmulWeightTensorPlacementRequest
                      formattedName
                      routerId
                      (FunCall "expert_id" [Var "e"])
                      (expertTensorPlacementId name routerId)
              ]
        ]
   where
    formattedName =
      FunCall
        "fmt::format"
        [LiteralExpr (StringLit (mungeSafetensorsKey template)), Var "e"]

  tensorPlacementIds = expertTensorPlacementIds run

  expertTensorPlacementId name routerId =
    fromMaybe
      ( error $
          "TronCpp.visitNamedTensorsMethod: no tensor ID for "
            ++ show name
            ++ " under "
            ++ show routerId
      )
      (M.lookup (routerId, name) tensorPlacementIds)

ordinaryTensorPlacementRequest :: Expr -> Expr
ordinaryTensorPlacementRequest name =
  FunCall
    ( NamespacedFun
        (LiteralType "hardware::tensor_placement_request")
        "ordinary_tensor"
    )
    [name]

attentionKeyProjectionTensorPlacementRequest :: Expr -> Expr
attentionKeyProjectionTensorPlacementRequest name =
  FunCall
    ( NamespacedFun
        (LiteralType "hardware::tensor_placement_request")
        "attention_key_projection_tensor"
    )
    [name]

attentionValueProjectionTensorPlacementRequest :: Expr -> Expr
attentionValueProjectionTensorPlacementRequest name =
  FunCall
    ( NamespacedFun
        (LiteralType "hardware::tensor_placement_request")
        "attention_value_projection_tensor"
    )
    [name]

moeRouterTensorPlacementRequest :: Expr -> Expr
moeRouterTensorPlacementRequest name =
  FunCall
    ( NamespacedFun
        (LiteralType "hardware::tensor_placement_request")
        "moe_router_tensor"
    )
    [name]

moeRouterIdExpr :: MoeRouterId -> Expr
moeRouterIdExpr routerId =
  BraceInit
    (LiteralType "moe_router_id")
    [LiteralExpr $ IntLit $ unMoeRouterId routerId]

moeMatmulWeightTensorPlacementRequest
  :: Expr -> MoeRouterId -> Expr -> ExpertTensorId -> Expr
moeMatmulWeightTensorPlacementRequest name routerId expert tensorId =
  FunCall
    ( NamespacedFun
        (LiteralType "hardware::tensor_placement_request")
        "moe_matmul_weight_tensor"
    )
    [ name
    , BraceInit
        (LiteralType "expert_tensor_coordinate")
        [ BraceInit
            (LiteralType "expert_coordinate")
            [moeRouterIdExpr routerId, expert]
        , BraceInit
            (LiteralType "expert_tensor_id")
            [LiteralExpr $ IntLit $ unExpertTensorId tensorId]
        ]
    ]

-- | Strip ".weight" suffix from safetensors key if present.  The Tron loader
-- | puts it back, or loads in GPTQ format if that's what's in the safetensors
-- | file.
mungeSafetensorsKey :: String -> String
mungeSafetensorsKey key =
  if ".weight" `List.isSuffixOf` key
    then take (length key - length (".weight" :: String)) key
    else key

stateStruct :: String -> Module -> StructDef
stateStruct implName m@Module{modDecls = env, mainKernel = run, logitsMunge} =
  StructDef "state" [] $
    [ LiteralDef $ implName ++ " const& model;"
    , LiteralDef $ "tron::model<" ++ implName ++ ">::state& outer_state;"
    ]
      ++ map (FieldDef . bufferField m) (getBuffers env)
      ++ concatMap (map FieldDef . moeRoutingFields) (getMoeRoutings env)
      ++ [ FieldDef $ moeScheduleField env routerId info
         | (routerId, info) <- moeRouters run
         ]
      ++ routingSyncFields env
      ++ concatMap (map FieldDef . expertViewFields) (getExpertViews env)
      ++ [ ConstructorDef $ stateConstructor implName m
         , MethodDef $ resizeMethod m
         , LiteralDef "void make_latches(latch_arena&) noexcept { }" -- No latches in the state itself
         , MethodDef $ runMethod m
         , MethodDef $ runHelpMethod m
         ]
      ++ map MethodDef (runAttentionWorkerMethods m)
      ++ [ MethodDef $ availableMainParallelismMethod env
         , -- Typed logits post-processing is applied here when present;
           -- otherwise the logits pass through.
           MethodDef $ patchLogitsMethod logitsMunge
         , MethodDef $ patchLogitsInPlaceMethod logitsMunge
         ]
      ++ concatMap (map MethodDef . kernelMethods env) (getKernels env)
      ++ concatMap (map MethodDef . moeBlendMethods env) (collectMoeBlends run)

-- | C++ expression applying the model's typed logits post-processing. A
-- scale division by a power-of-two constant (e.g. Granite's @/ 16.0@) is
-- emitted as a multiply by the exactly representable reciprocal; otherwise
-- the original operator is kept.
--
-- Returns @Nothing@ when the logits pass through unchanged.
logitsMungeExpr :: Maybe LogitsMunge -> Expr -> Maybe Expr
logitsMungeExpr Nothing _ = Nothing
logitsMungeExpr (Just (LogitsScale op c)) operand =
  Just $ logitsScaleExpr op c operand
logitsMungeExpr (Just (LogitsSoftcap c mScale)) operand =
  validateLogitsSoftcap c `seq`
    Just
      ( BinOp
          Mul
          (FunCall "tanh" [BinOp Div scaledOperand cap])
          cap
      )
 where
  cap = LiteralExpr $ FloatLit $ realToFrac c
  scaledOperand = case mScale of
    Nothing -> operand
    Just scale -> logitsScaleExpr BinaryMul scale operand

logitsScaleExpr :: BinaryOp -> Double -> Expr -> Expr
logitsScaleExpr op c operand =
  validateLogitsScale op c `seq`
    BinOp cppOp operand (LiteralExpr $ FloatLit floatLit)
 where
  recip' = 1.0 / c
  -- Prefer multiply-by-reciprocal when the reciprocal round-trips
  -- exactly through Float (true for powers of two such as 1/16).
  recipExact =
    (realToFrac (realToFrac recip' :: Float) :: Double) * c == 1.0
  (cppOp, floatLit) = case op of
    BinaryDiv
      | recipExact -> (Mul, realToFrac recip')
      | otherwise -> (Div, realToFrac c)
    BinaryMul -> (Mul, realToFrac c)
    _ -> error $ "logitsScaleExpr: unsupported logits-scale op " ++ show op

validateLogitsScale :: BinaryOp -> Double -> ()
validateLogitsScale op c
  | isNaN c || isInfinite c =
      error $
        "logitsMungeExpr: logits scale must be finite; got " ++ show c
  | op == BinaryDiv && c == 0 =
      error "logitsMungeExpr: logits scale divisor must be nonzero"
  | otherwise = ()

validateLogitsSoftcap :: Double -> ()
validateLogitsSoftcap c
  | isNaN c || isInfinite c || c <= 0 =
      error $
        "logitsMungeExpr: logits softcap must be finite and positive; got "
          ++ show c
  | otherwise = ()

-- | @patch_logits@ method body for the @state@ struct.
patchLogitsMethod :: Maybe LogitsMunge -> Method
patchLogitsMethod munge =
  Method "void" "patch_logits" params [MethodNoexcept] $
    Block
      [ ExprStmt $
          MethodCall
            (Var "logits_out")
            "set"
            [fromMaybe (Var "logits_in") (logitsMungeExpr munge (Var "logits_in"))]
      ]
 where
  params = [Param "auto&" "logits_in", Param "auto&" "logits_out"]

-- | @patch_logits_in_place@ method body for the @state@ struct.
patchLogitsInPlaceMethod :: Maybe LogitsMunge -> Method
patchLogitsInPlaceMethod munge =
  Method "void" "patch_logits_in_place" [Param "auto&" "logits"] [MethodNoexcept] $
    case logitsMungeExpr munge (Var "logits") of
      Nothing -> Block []
      Just expr -> Block [ExprStmt $ MethodCall (Var "logits") "set" [expr]]

-- | Dummy fixtures backing MoeRouting sync channels. Present on
-- @state@ only if at least one routing channel exists; the channel
-- is @fallback_producer_t@ and never touches either field at
-- runtime. See Note [MoeRouting Channel] in Tron.hs.
routingSyncFields :: Decls -> [StructComponent]
routingSyncFields env
  | any hasGuardChannel (getMoeRoutings env) =
      -- Both fields are referenced by every routing channel's
      -- constructor but never read at runtime (fallback latches skip
      -- buffer/items access). Default-construct them empty.
      [ LiteralDef
          "indexed_vector<singleton_id, itensor_t<1>> _routing_sync_buf;"
      , LiteralDef "std::vector<singleton_id> _singleton_items;"
      ]
  | otherwise = []
 where
  hasGuardChannel (_, info) = isJust $ moeRoutingGuardChannel info

stateConstructor :: String -> Module -> Constructor
stateConstructor implName mod =
  Constructor "state" constructorParams initializers $
    Block [runtimeLayerTruncationAssert "outer_state.cfg.max_layers"]
 where
  constructorParams =
    [ Param (fromString $ implName ++ " const&") "model"
    , Param (fromString $ "tron::model<" ++ implName ++ ">::state&") "outer_state"
    , ParamLit "model_config const&"
    ]
  initializers =
    [ Initializer "model" [Var "model"]
    , Initializer "outer_state" [Var "outer_state"]
    ]
      ++ mapMaybe (referenceBufferInitializer mod) (getBuffers $ modDecls mod)
      ++ map expertViewInitializer (getExpertViews $ modDecls mod)

-- Generated run bodies are statically unrolled over the full operation schedule;
-- a partial runtime layer count is not representable.
runtimeLayerTruncationAssert :: String -> Cpp.Statement
runtimeLayerTruncationAssert maxLayers =
  LitStmt $
    concat
      [ "TRON_ASSERT("
      , maxLayers
      , " == -1 || "
      , maxLayers
      , " == static_cast<int>(n_layers), "
      , "\"Ingest-generated models do not support partial runtime layer truncation: "
      , "requested {} of {} layers; ingest a model with the requested layer count "
      , "instead\", "
      , maxLayers
      , ", n_layers);"
      ]

resizeMethod :: Module -> Method
resizeMethod mod =
  Method "void" "resize" [Param "size_t" "max_tokens"] [] $
    Block $
      mapMaybe (resizeStatement mod) (getBuffers env)
        ++ concatMap moeRoutingResizeStatements (getMoeRoutings env)
 where
  env = modDecls mod

resizeStatement :: Module -> (Name ('Tron 'Buffer), BufferInfo) -> Maybe Cpp.Statement
resizeStatement mod (name, bufInfo) = case referenceBuffer mod name of
  -- A reference buffer aliases storage of outer_state (the framework's
  -- tron::model<...>::state), which resizes it after the plugin state.
  Just _ -> Nothing
  Nothing -> Just $ ExprStmt $ MethodCall (Var $ asCpp name) "resize" [resizeArg]
 where
  resizeArg = case bufferIterSpace bufInfo of
    QBatchItems -> Var "max_tokens"
    Fin (Static sz) -> LiteralExpr (Cpp.IntLit sz)
    -- A Fin buffer whose extent is @c * BatchSize@ has one runtime row
    -- for each of @c@ per-token lanes, so the state allocation scales
    -- with @max_tokens@ rather than a compile-time BatchSize value.
    Fin (Sum [Prod c (Known BatchSize NE.:| [])] 0) ->
      BinOp Cpp.Mul (LiteralExpr (Cpp.IntLit c)) (Var "max_tokens")
    Fin _ -> error "resizeStatement: Dynamic Fin iteration spaces not yet supported"
    MoeEntries _ -> error "resizeStatement: MoeEntries not yet supported"
    QBatchItemsExpertPairs _ n_chosen ->
      BinOp Cpp.Mul (Var "max_tokens") (LiteralExpr (Cpp.IntLit n_chosen))
    Singleton -> LiteralExpr (Cpp.IntLit 1)

-- | Generate resize statements for MoE routing auxiliary vectors.
moeRoutingResizeStatements
  :: (Name ('Tron 'MoeRouting), MoeRoutingInfo) -> [Cpp.Statement]
moeRoutingResizeStatements (name, _) =
  [ ExprStmt $
      MethodCall (Var $ derivedCppName name "per_token") "resize" [Var "max_tokens"]
  ]

-- Note [Ingested Model Mini-batching]
-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
-- Ingested models currently require --max-minibatches 1 because the generated
-- run() code processes batches sequentially while the hardware matmul launchers
-- and attention state are shared resources. The hand-written models (llama.hpp)
-- solve this with layer-major, batch-minor ordering that carefully interleaves
-- operations across batches. Implementing that interleaving in code generation
-- is future work; until then we assert single-batch and rely on the scheduler
-- constraint.

runMethod :: Module -> Method
runMethod Module{modDecls = env, mainKernel = run} =
  Method "void" "run" runParams [] $
    Block $
      [ LitStmt
          "TRON_ASSERT(q_batches.size() == 1, \
          \\"Ingested models require --max-minibatches 1; \
          \see Note [Ingested Model Mini-batching] in TronCpp.hs\");"
      , LitStmt "plugin_batch* q_batch = &q_batches[0]->plugin_batch;"
      ]
        ++ runLaunchWorkers operations
        ++ concatMap
          ( runStatement
              env
              (M.fromList (moeRouters run))
              (moeBlendNames run)
              operationsById
          )
          run
        ++ [runAwaitWorkers]
 where
  runParams = [Param "auto&" "q_batches"]
  operations = attentionOperations run
  operationsById = attentionOperationsById run

-- | Prologue for the generated @run()@: decide the main-helper vs attention
-- worker split and launch both worker populations on the app pool, per
-- Note [Plugin-owned worker launch] in model.hpp.  Declares the @n_workers@
-- local that the generated kernel calls stripe over.  Safe to pair with
-- 'runAwaitWorkers' because the top-level @run()@ body never returns early
-- (early returns only occur inside lifted kernel methods; see
-- Note [MoeBlend Method Lifting]).
runLaunchWorkers :: [AttentionOperation] -> [Cpp.Statement]
runLaunchWorkers operations =
  [ LitStmt $
      List.intercalate
        "\n"
        workerSplitLines
  ]
    ++ [ ExprStmt $
           TemplateMethodCall
             (Var "outer_state")
             "assemble_attention_plan"
             (map attentionGeometryType operations)
             [Var "n_attn_workers"]
       | hasAttention
       ]
    ++ [ LitStmt $
           List.intercalate
             "\n"
             ( [ "for (auto& q_batch_ptr : q_batches)"
               , "  q_batch_ptr->reset_channels(n_attn_workers, n_workers);"
               , "latch_trigger workers_trigger(\
                 \n_main_helpers + n_attn_workers, \"workers done\");"
               , "latch_ref workers_done(&workers_trigger);"
               , "for (size_t i = 0; i < n_main_helpers; ++i)"
               , "  tp.enqueue_to(i, [this, &q_batches, &workers_done, i, n_workers]() {"
               , "    run_main_help(q_batches, 1 + i, n_workers);"
               , "    workers_done.count_down();"
               , "  });"
               ]
                 ++ if hasAttention
                   then
                     [ "for (size_t i = 0; i < n_attn_workers; ++i)"
                     , "  tp.enqueue_to(n_main_helpers + i,"
                     , "      [this, &q_batches, &workers_done, i, n_attn_workers]() {"
                     , "        run_attention_worker(q_batches, i, n_attn_workers);"
                     , "        workers_done.count_down();"
                     , "      });"
                     ]
                   else []
             )
       ]
 where
  hasAttention = not $ null operations
  workerSplitLines =
    [ "// Decide the worker split and launch helpers and attention workers."
    , "// See Note [Plugin-owned worker launch] in model.hpp."
    , "thread_pool& tp = app_pool();"
    , "const size_t n_main_helpers = outer_state.recommend_n_main_helpers();"
    , "TRON_ASSERT(n_main_helpers <= tp.num_workers(),"
    , "    \"generated plugin requested {} main helpers from an {}-worker \""
    , "    \"application pool\", n_main_helpers, tp.num_workers());"
    ]
      ++ attentionWorkerAssertions
      ++ [ "const size_t n_workers = 1 + n_main_helpers;"
         , if hasAttention
             then "const size_t n_attn_workers = tp.num_workers() - n_main_helpers;"
             else "const size_t n_attn_workers = 0;"
         ]
  attentionWorkerAssertions
    | hasAttention =
        [ "TRON_ASSERT(n_main_helpers < tp.num_workers(),"
        , "    \"generated attention requires at least one application-pool \""
        , "    \"worker ({} helpers, {} pool workers)\", n_main_helpers,"
        , "    tp.num_workers());"
        ]
    | otherwise = []

-- | Epilogue for the generated @run()@: wait for the workers launched by
-- 'runLaunchWorkers', as Note [Plugin-owned worker launch] requires.
runAwaitWorkers :: Cpp.Statement
runAwaitWorkers =
  LitStmt $
    List.intercalate
      "\n"
      [ "// All the workers we spawned must be done before run() returns."
      , "// See Note [Plugin-owned worker launch] in model.hpp."
      , "workers_done.wait();"
      ]

runHelpMethod :: Module -> Method
runHelpMethod Module{modDecls = env, mainKernel = run} =
  Method "void" "run_main_help" runHelpParams [] $
    Block $
      [ LitStmt
          "TRON_ASSERT(q_batches.size() == 1, \
          \\"Ingested models require --max-minibatches 1; \
          \see Note [Ingested Model Mini-batching] in TronCpp.hs\");"
      , LitStmt "plugin_batch* q_batch = &q_batches[0]->plugin_batch;"
      ]
        ++ concatMap (runHelperStatement env (moeBlendNames run)) run
 where
  runHelpParams = [Param "auto&" "q_batches", Param "size_t" "worker_ix", Param "size_t" "n_workers"]

-- Note [Generated attention operation phases]
-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
-- Attention operations are an ingest-known sequence, so generated main and
-- worker code execute them in the same order. The existing scratchpad barrier
-- is also the operation phase: main advances it with a scratchpad reset in the
-- between-phases action, and workers wait for that phase before running. Early
-- HW preparation runs inside that action; late HW preparation runs after the
-- current-token K/V saves. See Note [Early and late hardware attention launch]
-- in model.hpp. Each operation ends with the existing worker 'done' calls. This
-- avoids per-operation latches and prevents reset or preparation from overtaking
-- the preceding operation.

-- | Emit the immutable attention-worker side of the operation schedule. Each
-- worker observes the same operation order as the main statement stream and
-- cannot enter an operation until the main thread advances the barrier phase.
-- With aligned lanes there are two programs, and the @run_attention_worker@
-- dispatcher picks one per pass. @run_attention_worker_helpers_only@ runs
-- only the attention jobs. @run_attention_worker_aligned@ also runs this
-- worker's share of the aligned lane domain. See Note [Aligned lane domain].
runAttentionWorkerMethods :: Module -> [Method]
runAttentionWorkerMethods m@(Module env _ run _ _ _ _)
  | hasAlignedLanes m =
      [ attentionWorkerDispatcher
      , attentionWorkerMethod "run_attention_worker_helpers_only" [] (const [])
      , attentionWorkerMethod
          "run_attention_worker_aligned"
          (laneAgreementAssert : windowCall Nothing)
          (windowCall . Just . attentionOpId)
      ]
        ++ [ laneWindowMethod (laneWindowName key) steps
           | (key, steps) <- windows
           , not (null steps)
           ]
  | otherwise = [attentionWorkerMethod "run_attention_worker" [] (const [])]
 where
  windows = laneWindows env run
  windowCall key = case lookup key windows of
    Just (_ : _) ->
      [ ExprStmt $
          FunCall
            (NamedFun $ laneWindowName key)
            [Var "q_batch", Var "worker_ix", Var "n_attn_workers"]
      ]
    _ -> []
  attentionWorkerMethod name prologue afterJob =
    Method "void" name params [] $
      Block $
        [ LitStmt
            "TRON_ASSERT(q_batches.size() == 1, \
            \\"Ingested models require --max-minibatches 1; \
            \see Note [Ingested Model Mini-batching] in TronCpp.hs\");"
        , LitStmt "plugin_batch* q_batch = &q_batches[0]->plugin_batch;"
        , Declare "uint64_t" "attn_elapsed" (Just $ LiteralExpr $ IntLit 0)
        ]
          ++ prologue
          ++ concatMap
            (\operation -> attentionWorkerOperation env operation ++ afterJob operation)
            (attentionOperations run)
          ++ [ IfStmt
                 (ExprLit "worker_ix == 0")
                 ( Block
                     [ ExprStmt $
                         MethodCall
                           (Var "outer_state")
                           "record_attention_time"
                           [Cpp.times (Var "attn_elapsed") (Var "n_attn_workers")]
                     ]
                 )
                 Nothing
             ]
  attentionWorkerDispatcher =
    Method "void" "run_attention_worker" params [] $
      Block
        [ Cpp.Comment "See Note [Aligned lane domain] in ingest/src/TronCpp.hs."
        , IfStmt
            (ExprLit "q_batches[0]->plugin_batch.n_attention_lanes == 0")
            ( Block
                [ ExprStmt $ FunCall "run_attention_worker_helpers_only" workerArgs
                , ReturnStmt Nothing
                ]
            )
            Nothing
        , ExprStmt $ FunCall "run_attention_worker_aligned" workerArgs
        ]
  workerArgs = [Var "q_batches", Var "worker_ix", Var "n_attn_workers"]
  -- reset_channels sized each lane channel for n_attention_lanes attention
  -- workers. Check that this worker's n_attn_workers is the same number.
  -- See Note [Aligned lane domain].
  laneAgreementAssert =
    LitStmt $
      List.intercalate
        "\n"
        [ "TRON_ASSERT(q_batch->n_attention_lanes == n_attn_workers,"
        , "    \"{} attention workers joined a pass reset for {} attention lanes\","
        , "    n_attn_workers, q_batch->n_attention_lanes);"
        ]
  params =
    [ Param "auto&" "q_batches"
    , Param "size_t" "worker_ix"
    , Param "size_t" "n_attn_workers"
    ]

-- | One step of an attention worker's window method.
data LaneStep
  = -- | Lane-side synchronization of a lane channel.
    LaneSync Cpp.Statement
  | -- | A guarded call that runs this worker's lane of an aligned-lane kernel
    -- or blend.
    LaneCall Cpp.Statement

-- | The attention workers' steps for each attention window, in main's order.
-- The windows split main's statements at each attention operation. Window
-- @Just k@ holds the statements after attention operation @k@, and window
-- 'Nothing' holds those before the first. A window's steps are the lane-side
-- synchronizations of lane channels and the calls to aligned-lane kernels and
-- blends among its statements. See Note [Aligned lane domain].
laneWindows :: Decls -> [Tron.Statement] -> [(Maybe AttentionOpId, [LaneStep])]
laneWindows env run = map (fmap (concatMap laneSteps)) $ attentionWindows run
 where
  blendNames = moeBlendNames run
  part = Var "part"
  laneSteps = \case
    ChannelStartWritingStmt c Tron.AllWorkers _
      | laneProducer c -> [LaneSync $ startWriting part c]
    ChannelFinishWritingStmt c Tron.AllWorkers _
      | laneProducer c -> [LaneSync $ finishWriting part c]
    ChannelStartReadingStmt c Tron.AllWorkers _
      | laneConsumer c ->
          [LaneSync $ startReading (channelReadParticipant env c part) c]
    ChannelFinishReadingStmt c Tron.AllWorkers _
      | laneConsumer c ->
          [LaneSync $ finishReading (channelReadParticipant env c part) c]
    HostStmt kernel _
      | ki <- readDecl kernel env
      , kernelLanes ki == AlignedLanes ->
          [laneCall (asCpp kernel) (not $ null $ kernelMatVecWeights $ kernelBody ki)]
    MoeBlendStmt r w o i b AlignedLanes _ ->
      [laneCall (blendNames M.! MoeBlendKey r w o i b AlignedLanes) False]
    _ -> []
  -- Attention workers pass touch = false to a router kernel's lane method.
  -- They own tokens only in a pass with more than twice as many tokens as
  -- helpers, and Note [MoE router warm-up] warms only in a pass with no more
  -- tokens than helpers.
  laneCall name router =
    LaneCall $
      IfStmt
        (Var "lane")
        ( Block
            [ ExprStmt $
                FunCall (NamedFun $ laneMethodName name) $
                  [Var "q_batch", ExprLit "*lane"]
                    ++ [LiteralExpr (BoolLit False) | router]
            ]
        )
        Nothing
  laneProducer c = case channelProducer (readDecl c env) of
    LaneP _ -> True
    _ -> False
  laneConsumer c =
    not $
      null
        [ ()
        | LaneConsumer _ <-
            NE.toList $ consumerDomains $ channelConsumer $ readDecl c env
        ]

-- | Main's statements split at each attention operation, keyed by the
-- operation they follow.
attentionWindows :: [Tron.Statement] -> [(Maybe AttentionOpId, [Tron.Statement])]
attentionWindows = go Nothing []
 where
  go key acc [] = [(key, reverse acc)]
  go key acc (AttentionStmt operation : rest) =
    (key, reverse acc) : go (Just $ attentionOpId operation) [] rest
  go key acc (stmt : rest) = go key (stmt : acc) rest

laneWindowName :: Maybe AttentionOpId -> Name Cpp
laneWindowName Nothing = "attention_prologue"
laneWindowName (Just (AttentionOpId k)) = fromString $ "attention_window_" ++ show k

-- | The method that attention worker @attn_ix@ runs for one attention window.
-- The worker takes its lane of the aligned stripe from
-- @tron::aligned_stripe_attention_lane@. On each lane channel it
-- synchronizes, it is participant @n_workers + attn_ix@, offset by the matrix
-- count on a mixed consumer. It takes part in every lane-channel phase in the
-- window, whether or not its lane has a token. It calls the lane method of a
-- kernel or blend only when it has a lane: the pass is large, and this lane
-- has a token.
laneWindowMethod :: Name Cpp -> [LaneStep] -> Method
laneWindowMethod name steps =
  Method "void" name params [] $
    Block $
      ( if null syncs
          then []
          else
            [ LitStmt "const size_t n_helpers = app_pool().num_workers() - n_attn_workers;"
            , LitStmt "const size_t n_workers = n_helpers + 1;"
            , LitStmt "const size_t part = n_workers + attn_ix;"
            ]
      )
        ++ [ LitStmt $
               "const std::optional<tron::lane> lane = tron::aligned_stripe_attention_lane(attn_ix, "
                 ++ "n_attn_workers, q_batch->items.size(), app_pool().num_workers());"
           | not $ null calls
           ]
        ++ map stepStatement steps
 where
  params =
    [ Param "plugin_batch*" "q_batch"
    , Param "size_t" "attn_ix"
    , Param "size_t" "n_attn_workers"
    ]
  syncs = [() | LaneSync _ <- steps]
  calls = [() | LaneCall _ <- steps]
  stepStatement (LaneSync stmt) = stmt
  stepStatement (LaneCall stmt) = stmt

attentionWorkerOperation :: Decls -> AttentionOperation -> [Cpp.Statement]
attentionWorkerOperation env stmt =
  [ ExprStmt $
      MethodCall
        (Var "outer_state")
        "wait_attention_job"
        [MemberAccess (Var "q_batch") "outer_batch", Var "worker_ix"]
  , ExprStmt $
      MethodCall
        (Var "outer_state")
        "help_drain_gof"
        [LiteralExpr $ IntLit 4]
  , IncAssignment
      (Var "attn_elapsed")
      Add
      ( TemplateMethodCall
          (Var "outer_state")
          "run_attention_job"
          (attentionOperationTemplateArgs stmt)
          [ MemberAccess (Var "q_batch") "outer_batch"
          , Var $ asCpp $ attentionQuery stmt
          , MemberAccess
              (Var "q_batch")
              (asCpp $ attentionChannel env $ attentionQuery stmt)
          , Var $ asCpp $ attentionOutput stmt
          , MemberAccess
              (Var "q_batch")
              (asCpp $ attentionChannel env $ attentionOutput stmt)
          , Var "worker_ix"
          , Var "n_attn_workers"
          ]
      )
  ]

attentionOpExpr :: AttentionOpId -> Cpp.Expr
attentionOpExpr =
  FunCall "attention_op_id" . pure . LiteralExpr . IntLit . unAttentionOpId

attentionBindingExpr :: AttentionOperation -> Cpp.Expr
attentionBindingExpr stmt =
  BraceInit
    "attention_binding"
    [ attentionOpExpr $ attentionOpId stmt
    , FunCall
        "model_layer_id"
        [LiteralExpr $ IntLit $ unModelLayerId $ attentionModelLayer stmt]
    , FunCall
        "kv_slot_id"
        [LiteralExpr $ IntLit $ unKvSlotId $ attentionKvSlot stmt]
    ]

attentionGeometryType :: AttentionOperation -> Cpp.Type
attentionGeometryType =
  ExprType . attentionGeometryExpr . attentionGeometry . attentionKernel

attentionOperationTemplateArgs :: AttentionOperation -> [Cpp.Type]
attentionOperationTemplateArgs stmt =
  [ attentionGeometryType stmt
  , ExprType $ LiteralExpr $ IntLit $ unAttentionOpId $ attentionOpId stmt
  ]

-- | Tells the framework the maximum useful main-helper striping per
-- minibatch.  Non-MoE: just @n_tokens@.  MoE: @n_tokens * top_k@,
-- because the expert loop stripes over (token, expert) slots.  When
-- multiple routings exist with distinct @top_k@, the largest wins —
-- only one MoE layer runs at a time, so this is the true bound.
availableMainParallelismMethod :: Decls -> Method
availableMainParallelismMethod env =
  Method
    "size_t"
    "available_main_parallelism"
    [Param "size_t" "n_tokens"]
    [Cpp.MethodConst, Cpp.MethodNoexcept]
    $ Block
      [ ReturnStmt $
          Just $
            Cpp.times (Var "n_tokens") (LiteralExpr (Cpp.IntLit factor))
      ]
 where
  factor = case [moeRoutingTopK info | (_, info) <- getMoeRoutings env] of
    [] -> 1
    ks -> toInteger (maximum ks)

newtype Locals = Locals (M.Map KernelVariable Expr)

insert :: Locals -> KernelVariable -> Expr -> Locals
insert (Locals m) var expr = Locals $ M.insert var expr m

-- Note [Aligned lane domain]
-- ~~~~~~~~~~~~~~~~~~~~~~~~~~
-- The aligned lane domain is a set of token-striped host kernels and blends
-- that share one stripe per pass. Its lanes are the helpers and, in passes
-- with more than twice as many tokens as helpers, the attention workers too.
-- This Note gives the lane rule, when the attention workers join the domain,
-- and why every lane channel's participant count matches the threads that
-- synchronize on it.
--
-- Membership. A host MoE router (Note [HostMatrix weights] in Tron.hs) runs
-- in the router kernel. That kernel fuses the residual add and rmsnorm before
-- the router with the top-k and softmax after it. The domain
-- holds the router kernels and the token-striped kernels and blends linked to
-- them through CPU-written per-token rows. Because they share one stripe, no
-- such row changes owner within a pass. Note [Aligned lane domain membership]
-- in LoopyTron/LaneDomain.hs gives the linking rule and the members for
-- GPT-OSS and Qwen3.
--
-- Lane rule. A pass has n tokens. n_workers counts main and the H helpers, so
-- H = n_workers - 1. A is the number of attention workers, and run() asserts
-- A >= 1. tron::aligned_stripe_num_lanes gives the number of lanes L(n):
--
--   L(n) = 1       if H = 0 (main runs the one lane)
--   L(n) = H       if H >= 1 and n <= 2H
--   L(n) = H + A   if H >= 1 and n > 2H
--
-- Lane l owns tokens l, l + L(n), l + 2 L(n), ... When H >= 1, main is not a
-- lane. The helper with worker_ix h (1 <= h <= H) is lane h - 1, and
-- attention worker j (0 <= j < A) is lane H + j;
-- tron::aligned_stripe_worker_lane and tron::aligned_stripe_attention_lane
-- give these lanes. With n <= 2H an attention worker would own at most one
-- token, so attention workers join the domain only in larger passes.
--
-- Joining the domain. J is true in a pass whose lanes include the attention
-- workers, that is, when H >= 1 and n > 2H. reset_channels computes J once
-- per pass with tron::is_large_pass, from n = items.size() and n_workers.
-- reset_channels runs on main before main enqueues any
-- worker. It stores A if J holds, and 0 otherwise, in
-- plugin_batch::n_attention_lanes. Enqueuing a worker publishes the value
-- to it. Attention workers only read it, and main writes it again only
-- after workers_done.wait(). The helpers take their stripe from
-- tron::aligned_stripe_worker_lane, which decides with tron::is_large_pass on
-- the same inputs, so J and the helpers' stripe cannot disagree.
--
-- Pool split. When the attention workers join the domain,
-- tron::aligned_stripe_num_lanes returns the pool size as the lane count
-- H + A. tron::aligned_stripe_attention_lane computes H as the pool size minus
-- A. Both assume
-- that the helpers and the attention workers together fill the application
-- pool, as Note [Attention workers are the last pool workers] in model.hpp
-- requires. reset_channels asserts this split every pass. The aligned
-- program also asserts that its A equals the n_attention_lanes that
-- reset_channels stored.
--
-- Lane channels. A lane channel is a channel with a LaneP producer or an
-- aligned-lane reader, that is, a LaneConsumer domain in its consumer. Each
-- such side is a lane side. A lane side has n_workers + n_attention_lanes
-- participants: main, the H helpers and, when J holds, the A attention
-- workers. Attention worker j is participant n_workers + j. On a mixed
-- consumer the lane-side ids are offset by the matrix count
-- (Note [Mixed parallel and matrix consumers] in Tron.hs). Every side that
-- is not a lane side keeps its usual count. In GPT-OSS and Qwen3, lane
-- channels carry five kinds of row. Lane sides read two: the o_proj output
-- and the moe_blend input. They write three: the top-k indices, the next
-- layer's QKV input, and the expert input. The expert input is the
-- normalized row that the router kernel writes and the expert matmuls read.
--
-- Attention worker programs. Each pass, run_attention_worker runs one of two
-- programs:
--   - Without J, run_attention_worker_helpers_only. It runs the attention jobs
--     and makes no call on a lane channel.
--   - With J, run_attention_worker_aligned. It runs the same attention jobs,
--     plus attention_prologue before the first job and attention_window_k
--     after job k.
-- Attention window k holds main's statements after attention operation k, up
-- to the next attention operation or the end of the pass. The prologue is the
-- attention window before the first attention operation. A window with no
-- lane-side work gets no method and no call. A window method runs, in main's
-- order, the lane side of each lane-channel synchronization in its window.
-- When the worker's lane owns tokens, it also runs the lane method of each
-- aligned-lane kernel and blend in the window.
--
-- Invariants. TronCheck enforces the static ones ('TronCheck.checkLaneDomain'):
--   L1. The kernels and blends that access a buffer without a guard channel
--       all have one stripe, so each of the buffer's rows has one owner in a
--       pass.
--   L2. The side opposite a lane side is never a helper-striped QBatchItems
--       kernel or an attention worker domain.
--   L3. No attention operation falls between the start and the finish of a
--       lane-side phase, so each attention window finishes every phase it
--       starts.
--   I6. An aligned-lane kernel or blend iterates over QBatchItems, and the
--       module has an attention operation.
-- The generated code maintains the rest:
--   - Aligned lanes need one minibatch. Every generated plugin asserts this
--     (Note [Ingested Model Mini-batching]).
--   - In every pass, the participants configured on a lane channel are
--     exactly the ids that call it: 0 to H, plus n_workers + j for each
--     attention worker j when J holds. A stray id aborts on the barrier's id
--     assert. A missing call hangs.
--   - J depends only on inputs that are constant within a pass. It holds
--     exactly when there are helpers and their stripe has H + A lanes.
--   - channel::reset re-sizes every barrier and latch each pass, so no
--     participant state crosses a pass boundary when J changes.
--
-- Deadlock freedom follows from ordering and needs no separate check.
-- Attention workers make their lane-side calls in main's order. So whenever
-- main waits on an attention worker, main has already issued every prepare
-- that the worker needed to reach that point.

-- | The methods of one kernel: the kernel itself and, on the aligned lane
-- domain, its lane method. See Note [Aligned lane domain].
kernelMethods :: Decls -> (Name ('Tron 'Kernel), KernelInfo) -> [Method]
kernelMethods env (name, ki) = case kernelLanes ki of
  HelperStripe -> [kernelMethod env (name, ki)]
  AlignedLanes ->
    alignedLaneMethods (asCpp name) (not $ null weights) $
      laneWarmUp weights
        ++ stripedLoop
          env
          name
          (kernelEntryReadBuffers ki)
          (kernelWriteBuffers ki)
          (Var "lane")
          (kernelIterSpace ki)
          (kernelVar ki)
          (\locals' -> kernelBodyStmts env locals' (kernelBody ki))
 where
  weights = kernelMatVecWeights (kernelBody ki)

-- | The parameters of a kernel method.
kernelParams :: [Param]
kernelParams =
  -- Can add Param "size_t" "layer" (in the second position) when we do layer abstraction.
  [ Param "plugin_batch*" "q_batch"
  , Param "size_t" "worker_ix"
  , Param "size_t" "n_workers"
  ]

-- | The two methods of an aligned-lane kernel or blend: an entry point for
-- main and the helpers, and a lane method with the given body. The entry
-- point takes the caller's lane of the aligned stripe from
-- @tron::aligned_stripe_worker_lane@, which is empty for main when helpers
-- exist, and passes it to the lane method. For a router kernel, the entry
-- point also passes the @touch@ flag of Note [MoE router warm-up]. Attention
-- workers call the lane method from their window methods.
alignedLaneMethods :: Name Cpp -> Bool -> [Cpp.Statement] -> [Method]
alignedLaneMethods name router laneBody =
  [ Method "void" name kernelParams [] $
      Block
        [ LitStmt $
            "const std::optional<tron::lane> lane = tron::aligned_stripe_worker_lane(worker_ix, n_workers, "
              ++ "q_batch->items.size(), app_pool().num_workers());"
        , LitStmt "if (!lane) { return; }"
        , ExprStmt $
            FunCall (NamedFun $ laneMethodName name) $
              [Var "q_batch", ExprLit "*lane"]
                ++ [ExprLit "tron::should_warm_router_weights(q_batch->items.size(), n_workers)" | router]
        ]
  , Method "void" (laneMethodName name) laneParams [] $ Block laneBody
  ]
 where
  laneParams =
    [ Param "plugin_batch*" "q_batch"
    , Param "tron::lane" "lane"
    ]
      ++ [Param "bool" "touch" | router]

-- | The name of the lane method of an aligned-lane kernel or blend.
laneMethodName :: Name Cpp -> Name Cpp
laneMethodName name = derivedCppName name "lane"

kernelMethod :: Decls -> (Name ('Tron 'Kernel), KernelInfo) -> Method
kernelMethod env (name, ki) = Method "void" (asCpp name) kernelParams [] body
 where
  body =
    Cpp.block
      [ case kernelIterSpace ki of
          QBatchItemsExpertPairs routingName n_chosen ->
            expertMajorStrategy
              env
              name
              routingName
              n_chosen
              buffers_read
              buffers_written
              (kernelVar ki)
              ( \locals' ->
                  kernelBodyStmts env locals' (kernelBody ki)
              )
          _ ->
            staticStrategy
              env
              name
              buffers_read
              buffers_written
              warmUp
              (kernelIterSpace ki)
              (kernelVar ki)
              (\locals' -> kernelBodyStmts env locals' (kernelBody ki))
      ]
  -- See Note [Fused kernel entry reads] in Loopy/KernelAccess.hs.
  buffers_read = kernelEntryReadBuffers ki
  buffers_written = kernelWriteBuffers ki
  warmUp = moeRouterWarmUp (kernelBody ki)

-- Note [Residual+RMSNorm Fusion]
-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
-- KernelFusion.fuseAdjacentKernels merges the residual `add` and the
-- following `rmsnorm` ParKernels (they share q_batch->items as their
-- outer iteration space) into one kernel body of the form
--
--   add_n[ix]  = embedding[ix] + linear_n[ix]
--   mul_n[ix]  = tron::rmsnorm(w, add_n[ix], eps)
--
-- The first statement rounds the fp32 sum to bf16 in `add_n`. The
-- unfused rmsnorm then reads `add_n` back from bf16 and so accumulates
-- its sum-of-squares from a bf16 source instead of the fp32 sum, which
-- loses precision. See issue #2155.
--
-- This pattern matcher recognises the fused body and emits a single call to
-- `tron::residual_and_rmsnorm(x_in, y, x_out, z, w, eps)` (the SSA overload
-- in h/tron/kernels/wide.hpp). `ShiftedRmsNorm` uses the same fusion with a
-- trailing static weight offset: `residual_and_rmsnorm(..., eps, 1.0f)`.
-- The bf16 store to `add_n` is preserved (subsequent layers' residual adds
-- read it), but both passes of the rmsnorm operate on x_in + y in fp32 -- pass 1
-- accumulates the sum-of-squares from the fp32 sum before rounding,
-- and pass 2 redoes the addition in fp32 instead of reading `add_n`
-- back from bf16.
--
-- We do NOT eliminate `add_n` from the env: the residual stream pattern
-- has multiple readers of the residual (the next block's residual add).
--
-- Ordinary scalar-weight rmsnorms are intentionally NOT fused here:
-- 'ternToCpp' emits the scalar broadcast around the unit-weight expression.
-- Shifted scalar weights are invalid and fail before complete C++ output. The
-- 6-arg ordinary and 7-arg shifted 'tron::residual_and_rmsnorm' overloads
-- require a rank-1 tensor weight, so the matcher only fuses that form.
-- The wide fused kernel also requires a positive multiple-of-16 element count.
-- If codegen cannot prove that property statically, it leaves the two
-- tail-safe expression operations separate.

-- | Emit a kernel-body statement list, recognising the residual+rmsnorm
-- pair (see Note above). Equivalent to @concatMap kernelBodyStmt@ except
-- that adjacent @Binary Add x y c : Ternary op w c eps z@ statements collapse
-- into a single @tron::residual_and_rmsnorm@ call for either RMSNorm op.
kernelBodyStmts :: Decls -> Locals -> [KernelStmt] -> [Cpp.Statement]
kernelBodyStmts _ _ [] = []
kernelBodyStmts env locals (Binary Ops.Add x y c : Ternary Ops.RmsNorm w c' eps z : rest)
  | c == c'
  , canFuseResidualRmsNorm env w c =
      residualRmsNormCall env locals x y c z w eps Nothing
        : kernelBodyStmts env locals rest
kernelBodyStmts
  env
  locals
  (Binary Ops.Add x y c : Ternary Ops.ShiftedRmsNorm w c' eps z : rest)
    | c == c'
    , canFuseResidualRmsNorm env w c =
        residualRmsNormCall env locals x y c z w eps (Just 1.0)
          : kernelBodyStmts env locals rest
kernelBodyStmts env locals (s : rest) =
  kernelBodyStmt env locals s ++ kernelBodyStmts env locals rest

-- | The fused residual+rmsnorm call, with an optional trailing weight offset.
residualRmsNormCall
  :: Decls
  -> Locals
  -> KernelExpr
  -> KernelExpr
  -> KernelExpr
  -> KernelExpr
  -> KernelExpr
  -> KernelExpr
  -> Maybe Float
  -> Cpp.Statement
residualRmsNormCall env locals x y c z w eps weightOffset =
  onlyStmt $
    withWritableKernelOutputs env locals [c, z] $ \case
      [cOut, zOut] ->
        ExprStmt
          ( FunCall
              "tron::residual_and_rmsnorm"
              ( [ kernelBodyExpr env locals x
                , kernelBodyExpr env locals y
                , cOut
                , zOut
                , kernelBodyExpr env locals w
                , kernelBodyExpr env locals eps
                ]
                  ++ maybe
                    []
                    (\offset -> [LiteralExpr (FloatLit offset)])
                    weightOffset
              )
          )
      _ -> error "residualRmsNormCall: impossible output arity"

-- | Whether @tron::residual_and_rmsnorm@ accepts these operands.
-- A missing static input extent keeps the operations separate.
canFuseResidualRmsNorm :: Decls -> KernelExpr -> KernelExpr -> Bool
canFuseResidualRmsNorm env weight input =
  isRank1RmsNormWeight env weight
    && maybe
      False
      (\width -> width > 0 && width `rem` 16 == 0)
      (staticKernelInputWidth env input)

-- | Whether an RMSNorm weight supplies one scale per normalized element.
isRank1RmsNormWeight :: Decls -> KernelExpr -> Bool
isRank1RmsNormWeight env weight =
  rmsNormWeightForm env weight == Rank1Tensor

data RmsNormWeightForm
  = ScalarExpression
  | Rank1Tensor
  | Rank2Tensor
  | OtherExpression
  deriving (Eq)

-- | Classify the C++ value used as an RMSNorm weight. A zero-rank loaded
-- tensor is not a scalar C++ expression and has no valid Tron tensor type.
rmsNormWeightForm :: Decls -> KernelExpr -> RmsNormWeightForm
rmsNormWeightForm _ KernelVarExpr{} = ScalarExpression
rmsNormWeightForm _ KernelTokenIndexExpr{} = ScalarExpression
rmsNormWeightForm _ KernelBuffer{} = Rank2Tensor
rmsNormWeightForm env (KernelInput input) =
  case inputShape $ readDecl input env of
    [_] -> Rank1Tensor
    [_, _] -> Rank2Tensor
    _ -> OtherExpression
rmsNormWeightForm env (KernelParam param) =
  case shape $ readDecl param env of
    [_] -> Rank1Tensor
    [_, _] -> Rank2Tensor
    _ -> OtherExpression
rmsNormWeightForm _ KernelConfig{} = ScalarExpression
rmsNormWeightForm _ KernelExpertView{} = Rank2Tensor
rmsNormWeightForm _ KernelPermutation{} = OtherExpression
rmsNormWeightForm env (KernelIndexExpr base _) =
  case rmsNormWeightForm env base of
    Rank1Tensor -> ScalarExpression
    Rank2Tensor -> Rank1Tensor
    _ -> OtherExpression
rmsNormWeightForm _ KernelSliceExpr{} = Rank1Tensor
rmsNormWeightForm _ KernelLiteral{} = ScalarExpression

-- | Recover a kernel input's compile-time last-dimension extent.
staticKernelInputWidth :: Decls -> KernelExpr -> Maybe Integer
staticKernelInputWidth _ (KernelSliceExpr _ _ width) = Just width
staticKernelInputWidth env (KernelIndexExpr base _) = staticKernelInputWidth env base
staticKernelInputWidth env (KernelBuffer buffer) =
  staticInteger $ bufferWidth $ readDecl buffer env
staticKernelInputWidth env (KernelInput input) =
  lastStatic $ inputShape $ readDecl input env
staticKernelInputWidth env (KernelParam param) =
  lastStatic $ shape $ readDecl param env
staticKernelInputWidth _ _ = Nothing

staticInteger :: Expr -> Maybe Integer
staticInteger (LiteralExpr (IntLit value)) = Just value
staticInteger _ = Nothing

lastStatic :: [Expr] -> Maybe Integer
lastStatic [] = Nothing
lastStatic xs = staticInteger $ last xs

kernelBodyStmt :: Decls -> Locals -> KernelStmt -> [Cpp.Statement]
kernelBodyStmt env locals (Unary op inputArg outputArg) =
  unaryToCpp env locals op inputArg outputArg
kernelBodyStmt env locals (Binary op input1 input2 outputArg) =
  binaryToCpp env locals op input1 input2 outputArg
kernelBodyStmt env locals (Ternary op in1 in2 in3 outputArg) =
  ternToCpp env locals op in1 in2 in3 outputArg
kernelBodyStmt env locals (TopK input k largest sorted indicesOut valuesOut) =
  -- topk writes to both indices and values; all args passed to the C++ call.
  -- When k is a compile-time literal and the operation is the canonical
  -- MoE-routing shape (largest=true, sorted=true), specialize only when
  -- 0 < K <= N is proven. The general call handles zero and clamps oversized K.
  case (k, largest, sorted) of
    ( KernelLiteral (LiteralExpr (IntLit kVal))
      , KernelLiteral (LiteralExpr (BoolLit True))
      , KernelLiteral (LiteralExpr (BoolLit True))
      )
        | kVal > 0
        , Just width <- staticKernelInputWidth env input
        , kVal <= width ->
            withWritableKernelOutputs env locals [indicesOut, valuesOut] $ \case
              [indicesOutExpr, valuesOutExpr] ->
                ExprStmt $
                  TemplateFunCall
                    "tron::topk_fixed"
                    [ExprType (LiteralExpr (IntLit kVal))]
                    [kernelBodyExpr env locals input, indicesOutExpr, valuesOutExpr]
              _ -> error "kernelBodyStmt TopK: impossible output arity"
    _ ->
      -- General case: input size deduced inside tron::topk via Input::size_.
      withWritableKernelOutputs env locals [indicesOut, valuesOut] $ \case
        [indicesOutExpr, valuesOutExpr] ->
          ExprStmt $
            FunCall
              "tron::topk"
              ( map
                  (kernelBodyExpr env locals)
                  [input, k, largest, sorted]
                  ++ [indicesOutExpr, valuesOutExpr]
              )
        _ -> error "kernelBodyStmt TopK: impossible output arity"
kernelBodyStmt env locals (StridedCopy src offset stride count dst) =
  -- strided_copy is a void function: strided_copy(src, offset, stride, count, dst)
  let inputExprs = map (kernelBodyExpr env locals) [src, offset, stride, count]
   in withWritableKernelOutput env locals dst $ \dstExpr ->
        ExprStmt $ FunCall "tron::strided_copy" $ inputExprs ++ [dstExpr]
kernelBodyStmt env locals (BackPermute permName src dst) =
  -- dst.set_and_flush(tron::back_permute(model.<perm>, src))
  -- The 'permName' is the permutation 'Name' declared by the paired
  -- 'L.Load2' in BulkLoopy and bound to a 'PermutationInfo' entry by
  -- 'LoopyTron.translateEnvStmt'.
  let dstExpr = kernelBodyExpr env locals dst
      srcExpr = kernelBodyExpr env locals src
      permRef = FieldRef (Var "model") (asCpp permName)
      rhs = FunCall "tron::back_permute" [permRef, srcExpr]
   in case dst of
        KernelSliceExpr{} -> [assignKernelOutput env locals dst rhs]
        _ -> [ExprStmt $ MethodCall dstExpr "set_and_flush" [rhs]]
kernelBodyStmt env locals (Reduce op inputArg outputArg) =
  let inputExpr = kernelBodyExpr env locals inputArg
      fname = case op of
        Ops.ReduceSum -> "tron::sum"
        Ops.ReduceMean -> "tron::mean"
   in [assignKernelOutput env locals outputArg (FunCall fname [inputExpr])]
kernelBodyStmt env locals (Nary fname inputArgs outputArg) =
  let inputExprs = map (kernelBodyExpr env locals) inputArgs
   in [assignKernelOutput env locals outputArg (FunCall fname inputExprs)]
kernelBodyStmt env locals (LogStmt obj width var tag layer) =
  let objExpr = kernelBodyExpr env locals obj
   in [logIntermediate objExpr width (Var (asCpp var)) tag layer]
kernelBodyStmt env locals (For var iterSpace body) =
  [ serialStrategy $
      resolveIterationSpace
        env
        var
        iterSpace
        ( \locals' ->
            kernelBodyStmts env locals' body
        )
        locals
  ]
kernelBodyStmt _ _ (Tron.Comment text) =
  [Cpp.Comment text]

logIntermediate :: Expr -> Expr -> Expr -> String -> Maybe Expr -> Cpp.Statement
logIntermediate obj width var tag Nothing =
  ExprStmt $
    FunCall
      "outer_state.log_intermediate"
      [obj, width, var, LiteralExpr (StringLit tag)]
logIntermediate obj width var tag (Just layer) =
  ExprStmt $
    FunCall
      "outer_state.log_intermediate"
      [obj, width, var, LiteralExpr (StringLit (tag ++ " layer {}")), layer]

-- | Assign into a kernel output expression.
--
-- A slice expression is a temporary @tron::slice<N>@ proxy, so writes must go
-- through its @set@ method. Ordinary kernel outputs are still true lvalues and
-- can use direct assignment.
assignKernelOutput :: Decls -> Locals -> KernelExpr -> Expr -> Cpp.Statement
assignKernelOutput env locals outputArg rhs
  | KernelSliceExpr{} <- outputArg =
      ExprStmt $ MethodCall outputExpr "set" [rhs]
  | otherwise = Assignment outputExpr rhs
 where
  outputExpr = kernelBodyExpr env locals outputArg

-- | Collapse helpers that are expected to emit exactly one statement.
onlyStmt :: [Cpp.Statement] -> Cpp.Statement
onlyStmt [stmt] = stmt
onlyStmt stmts = error $ "onlyStmt: expected one statement, got " ++ show (length stmts)

-- | Run a statement builder with a writable expression for one kernel output.
withWritableKernelOutput
  :: Decls -> Locals -> KernelExpr -> (Expr -> Cpp.Statement) -> [Cpp.Statement]
withWritableKernelOutput env locals outputArg build =
  withWritableKernelOutputs env locals [outputArg] $ \case
    [outputExpr] -> build outputExpr
    _ -> error "withWritableKernelOutput: impossible output arity"

-- | Run a statement builder with writable expressions for kernel outputs.
--
-- Some helper APIs take output references, but @tron::slice<N>@ is produced as
-- an expression, not an lvalue variable. When any output is a slice, introduce
-- local @auto@ bindings for the slice proxies and pass those variables to the
-- builder.
withWritableKernelOutputs
  :: Decls -> Locals -> [KernelExpr] -> ([Expr] -> Cpp.Statement) -> [Cpp.Statement]
withWritableKernelOutputs env locals outputArgs build
  | any isSlice outputArgs =
      [Block $ catMaybes decls ++ [build outputExprs]]
  | otherwise = [build outputExprs]
 where
  outputExprs = zipWith outputExpr [0 :: Int ..] outputArgs
  decls = zipWith outputDecl [0 :: Int ..] outputArgs

  outputExpr ix arg
    | isSlice arg = Var $ sliceOutputName ix
    | otherwise = kernelBodyExpr env locals arg

  outputDecl ix arg
    | isSlice arg =
        Just $
          Declare
            (LiteralType "auto")
            (sliceOutputName ix)
            (Just $ kernelBodyExpr env locals arg)
    | otherwise = Nothing

  sliceOutputName ix = fromString $ "__slice_out_" ++ show ix

  isSlice KernelSliceExpr{} = True
  isSlice _ = False

-- | Translate a unary op to its C++ expression form.
unaryToCpp
  :: Decls -> Locals -> Ops.UnOp -> KernelExpr -> KernelExpr -> [Cpp.Statement]
unaryToCpp env locals op inputArg outputArg =
  case op of
    Ops.Sigmoid -> assignFunOp "tron::sigmoid"
    Ops.Softmax -> assignFunOp "tron::softmax"
    Ops.GeLU -> panic "unaryToCpp: exact GELU has no device implementation"
    Ops.GeLUTanh -> assignFunOp "tron::gelu_tanh"
    Ops.Copy
      | KernelIndexExpr (KernelInput input) _ <- inputArg
      , Just _ <- tokenJobInputType env input ->
          withWritableKernelOutput env locals outputArg $ \outputExpr ->
            ExprStmt $
              FunCall "tron::strided_copy" $
                [inputExpr] ++ map (LiteralExpr . IntLit) [0, 1, 1] ++ [outputExpr]
      | otherwise -> [assignKernelOutput env locals outputArg inputExpr]
    Ops.Swish -> assignFunOp "tron::swish"
    _other -> panic $ "unaryToCpp: Unsupported C++ operation " PP.<+> PP.pretty op
 where
  assignFunOp name =
    [assignKernelOutput env locals outputArg $ FunCall name [inputExpr]]

  inputExpr = kernelBodyExpr env locals inputArg

-- | Translate a binary op to its C++ expression form.
binaryToCpp
  :: Decls
  -> Locals
  -> Ops.BinOp
  -> KernelExpr
  -> KernelExpr
  -> KernelExpr
  -> [Cpp.Statement]
binaryToCpp env locals op input1Arg input2Arg outputArg =
  case op of
    Ops.Add -> assignBinOp Add
    Ops.Mul -> assignBinOp Mul
    Ops.Div -> assignBinOp Div
    Ops.Index -> [assignKernelOutput env locals outputArg $ Index inputExpr1 inputExpr2]
    -- swish_mul is always flushed; output is passed as argument
    Ops.SwishMul ->
      withWritableKernelOutput env locals outputArg $ \outputExpr ->
        ExprStmt $ FunCall "tron::swish_mul<true>" [inputExpr1, inputExpr2, outputExpr]
    -- See Note [Kernel matrix-vector products] in Ops.hs.
    Ops.MatVec ->
      withWritableKernelOutput env locals outputArg $ \outputExpr ->
        ExprStmt $ MethodCall inputExpr1 "matvec" [outputExpr, inputExpr2]
    _other -> panic $ "binaryToCpp: Unsupported C++ operation " PP.<+> PP.pretty op
 where
  assignBinOp f =
    [assignKernelOutput env locals outputArg $ BinOp f inputExpr1 inputExpr2]

  inputExpr1 = kernelBodyExpr env locals input1Arg
  inputExpr2 = kernelBodyExpr env locals input2Arg

-- | Translate a ternary op to its C++ expression form.
ternToCpp
  :: Decls
  -> Locals
  -> Ops.TernOp
  -> KernelExpr
  -> KernelExpr
  -> KernelExpr
  -> KernelExpr
  -> [Cpp.Statement]
ternToCpp env locals op in1Arg in2Arg in3Arg outputArg =
  case op of
    -- clamp is a void function: clamp(input, min, max, output)
    Ops.Clamp ->
      withWritableKernelOutput env locals outputArg $ \outputExpr ->
        ExprStmt $ FunCall "tron::clamp" $ inputExprs ++ [outputExpr]
    Ops.Rope -> assignFunOp "tron::rope"
    Ops.RmsNorm
      -- Unit weight (literal 1.0): emit 2-arg rmsnorm(input, epsilon)
      | KernelLiteral (LiteralExpr (FloatLit 1.0)) <- in1Arg ->
          let in2Expr = kernelBodyExpr env locals in2Arg
              in3Expr = kernelBodyExpr env locals in3Arg
           in [assignKernelOutput env locals outputArg $ FunCall "tron::rmsnorm" [in2Expr, in3Expr]]
      | ScalarExpression <- rmsNormWeightForm env in1Arg ->
          let weightExpr = kernelBodyExpr env locals in1Arg
              inputExpr = kernelBodyExpr env locals in2Arg
              epsilonExpr = kernelBodyExpr env locals in3Arg
              normalized = FunCall "tron::rmsnorm" [inputExpr, epsilonExpr]
           in [assignKernelOutput env locals outputArg $ BinOp Mul normalized weightExpr]
      | Rank1Tensor <- rmsNormWeightForm env in1Arg ->
          assignFunOp "tron::rmsnorm"
      | otherwise ->
          error
            "TronCpp.ternToCpp: RMSNorm weight must be a scalar C++ expression or a rank-1 tensor"
    Ops.ShiftedRmsNorm
      | Rank1Tensor <- rmsNormWeightForm env in1Arg ->
          [ assignKernelOutput env locals outputArg $
              FunCall
                "tron::rmsnorm"
                (inputExprs ++ [LiteralExpr (FloatLit 1.0)])
          ]
      | otherwise ->
          error
            "TronCpp.ternToCpp: shifted RMSNorm weight must be a rank-1 tensor"
    -- See Note [SwiGLU EqSat Recognition].
    -- 'tron::wide_swiglu' uses bf16 SIMD deinterleave intrinsics that
    -- don't compile against host float32 tensors; the scalar
    -- 'tron::host_swiglu' overload handles that case.
    Ops.SwiGLU ->
      withWritableKernelOutput env locals outputArg $ \outputExpr ->
        let args =
              [ kernelBodyExpr env locals in1Arg
              , outputExpr
              , kernelBodyExpr env locals in2Arg
              , kernelBodyExpr env locals in3Arg
              ]
         in IfConstexprStmt
              (ExprLit "!is_host")
              (Block [ExprStmt $ FunCall "tron::wide_swiglu" args])
              (Just $ Block [ExprStmt $ FunCall "tron::host_swiglu" args])
 where
  inputExprs = map (kernelBodyExpr env locals) [in1Arg, in2Arg, in3Arg]
  assignFunOp name =
    [assignKernelOutput env locals outputArg (FunCall name inputExprs)]

-- | The C++ element type of a framework-provided `indexed_vector` input or
-- 'Nothing' if not such an input.
-- See Note [Token-job input representation] in Loopy.hs.
tokenJobInputType :: Decls -> Name ('Tron 'Input) -> Maybe Cpp.Type
tokenJobInputType env input = case inputName (readDecl input env) of
  "token_job_tokens" -> Just "uint32_t"
  "token_job_positions" -> Just "uint32_t"
  _ -> Nothing

kernelBodyExpr :: Decls -> Locals -> KernelExpr -> Expr
kernelBodyExpr _ (Locals m) (KernelVarExpr var) = case M.lookup var m of
  Just expr -> expr
  Nothing -> error $ "kernelBodyExpr: local variable not found: " ++ show var
kernelBodyExpr _ _ (KernelBuffer buffer) = Var $ asCpp buffer
kernelBodyExpr env _ (KernelInput input) =
  let inputInfo = readDecl input env
      actualInputName = inputName inputInfo
   in FieldRef (Var "outer_state") (fromString actualInputName)
kernelBodyExpr _ _ (KernelParam param) = FieldRef (Var "model") $ asCpp param
kernelBodyExpr _ _ (KernelConfig config) = FieldRef (MemberAccess "this" "model") $ asCpp config
kernelBodyExpr _ _ (KernelExpertView ev) = Var $ asCpp ev
kernelBodyExpr _ _ (KernelPermutation pn) = FieldRef (Var "model") $ asCpp pn
-- Present each framework input element as a read-only, unaligned row.
-- See Note [Token-job input representation] in Loopy.hs.
kernelBodyExpr env locals (KernelIndexExpr obj@(KernelInput input) ix)
  | Just elementType <- tokenJobInputType env input =
      TemplateFunCall
        "tron::const_view"
        [ elementType
        , ExprType (LiteralExpr (BoolLit False))
        , ExprType (LiteralExpr (BoolLit False))
        , TemplateType "tron::seq" [ExprType (LiteralExpr (IntLit 1))]
        ]
        [AddrOf $ Index (kernelBodyExpr env locals obj) (kernelBodyExpr env locals ix)]
kernelBodyExpr env locals (KernelIndexExpr obj ix) =
  Index (kernelBodyExpr env locals obj) (kernelBodyExpr env locals ix)
kernelBodyExpr env locals (KernelTokenIndexExpr ix) =
  MethodCall (kernelBodyExpr env locals ix) "token" []
kernelBodyExpr env locals (KernelSliceExpr base off len) =
  Apply
    ( TemplateFunCall
        "tron::slice"
        [ExprType (LiteralExpr (IntLit len))]
        []
    )
    [kernelBodyExpr env locals base, off]
kernelBodyExpr _ _ (KernelLiteral lit) = lit

-- | A serial loop over an iteration space in C++: a loop variable ranging over
-- @[0, limit)@ and the body for one value of it ('serialStrategy'). Striped
-- kernels deal their items through 'stripedItems' instead.
data CppIter = CppIter
  { cppLoopvarType :: Type
  , cppLoopvar :: Name Cpp
  , cppLoopvarLimit :: Expr
  , cppIterBody :: [Cpp.Statement]
  }

resolveIterationSpace
  :: Decls
  -> KernelVariable
  -> IterationSpace
  -> (Locals -> [Cpp.Statement])
  -> Locals
  -> CppIter
resolveIterationSpace _ loopvar QBatchItems body locals = header body'
 where
  (header, access) = fieldBasedHeader "q_batch->items"
  cppLoopvar = asCpp loopvar
  remap = [Declare (LiteralType "token_job_id") cppLoopvar (Just access)]
  locals' = insert locals loopvar (Var cppLoopvar)
  body' = remap ++ body locals'
resolveIterationSpace env loopvar (Fin size) body locals = header body'
 where
  cppLoopvar = asCpp loopvar
  header =
    CppIter
      (LiteralType "size_t")
      cppLoopvar
      (sizeToCppWith (kernelBodyExpr env locals) size)
  locals' = insert locals loopvar (Var cppLoopvar)
  body' = body locals'
resolveIterationSpace _ loopvar (QBatchItemsExpertPairs _ n_chosen) body locals =
  header body'
 where
  cppLoopvar = asCpp loopvar
  (header, access) = fieldBasedHeader $ MemberAccess "q_batch" $ fromString $ expertPairItemsName n_chosen
  remap = [Declare (LiteralType "token_slot_id") cppLoopvar (Just access)]
  locals' = insert locals loopvar (Var cppLoopvar)
  body' = remap ++ body locals'
resolveIterationSpace _ _ (MoeEntries _) _ _ =
  error "resolveIterationSpace: MoeEntries not yet supported"
resolveIterationSpace _ _ Singleton _ _ =
  error "resolveIterationSpace: Singleton is a sync point, not iterable"

fieldBasedHeader :: Expr -> ([Cpp.Statement] -> CppIter, Expr)
fieldBasedHeader q_batch_field = (header, access)
 where
  header =
    CppIter
      (LiteralType "size_t")
      "task"
      (MethodCall q_batch_field "size" [])
  access = Index q_batch_field "task"

serialStrategy :: CppIter -> Cpp.Statement
serialStrategy iter = ForStmt init cond inc $ Block $ cppIterBody iter
 where
  var = cppLoopvar iter
  init = Cpp.Declare (cppLoopvarType iter) var (Just $ LiteralExpr (IntLit 0))
  cond = Cpp.BinOp Lt (Var var) (cppLoopvarLimit iter)
  inc = Cpp.IncAssignment (Var var) Add (LiteralExpr (IntLit 1))

-- | Bind @lane@ to the calling thread's lane of the helper stripe, returning
-- at once on main when helpers exist. See Note [Threads, stripes and lanes].
helperLaneSetup :: [Cpp.Statement]
helperLaneSetup =
  [ LitStmt
      "const std::optional<tron::lane> lane = tron::helper_stripe_lane(worker_ix, n_workers);"
  , LitStmt "if (!lane) { return; }"
  ]

-- Note [MoE router warm-up]
-- ~~~~~~~~~~~~~~~~~~~~~~~~~
-- In a pass where each lane of the helper stripe owns at most one token, a
-- thread whose lane owns a token loads a router kernel's host weights into its
-- cache before its first row arrives (tron::should_warm_router_weights).
-- Before its first row wait, it calls 'weight_matrix::touch', which reads one
-- 8-byte word from each 64-byte cache line.
--
-- In such a pass each helper runs at most one router matvec for the kernel.
-- Without the warm-up, that matvec takes the weights' cache misses after the
-- helper's o_proj row arrives, on the critical path. With it, the loads
-- overlap the wait. A larger pass amortizes the misses over several rows, so
-- its helpers skip the extra read.
--
-- On the aligned lane domain (Note [Aligned lane domain]), a helper passes
-- the same condition to the kernel's lane method as its @touch@ flag. An
-- attention worker passes false, because it owns tokens only when n > 2H.

-- | The warm-up of Note [MoE router warm-up] for a helper-striped kernel whose
-- body multiplies by host router weights. It is empty for any other kernel.
moeRouterWarmUp :: [KernelStmt] -> [Cpp.Statement]
moeRouterWarmUp body = case kernelMatVecWeights body of
  [] -> []
  weights ->
    [ Cpp.Comment "See Note [MoE router warm-up] in ingest/src/TronCpp.hs."
    , IfStmt
        ( ExprLit $
            "lane->ix < q_batch->items.size() && "
              ++ "tron::should_warm_router_weights(q_batch->items.size(), n_workers)"
        )
        (Block $ map touchWeights weights)
        Nothing
    ]

-- | The warm-up of an aligned-lane router kernel, gated by its @touch@
-- parameter and by its lane owning a token. See Note [MoE router warm-up].
laneWarmUp :: [Name ('Tron 'Tensor)] -> [Cpp.Statement]
laneWarmUp [] = []
laneWarmUp weights =
  [ Cpp.Comment "See Note [MoE router warm-up] in ingest/src/TronCpp.hs."
  , IfStmt
      (ExprLit "lane.ix < q_batch->items.size() && touch")
      (Block $ map touchWeights weights)
      Nothing
  ]

touchWeights :: Name ('Tron 'Tensor) -> Cpp.Statement
touchWeights w = ExprStmt $ MethodCall (FieldRef (Var "model") (asCpp w)) "touch" []

-- | Host router weights a kernel body multiplies by.
kernelMatVecWeights :: [KernelStmt] -> [Name ('Tron 'Tensor)]
kernelMatVecWeights = concatMap $ \case
  Binary Ops.MatVec (KernelParam w) _ _ -> [w]
  For _ _ stmts -> kernelMatVecWeights stmts
  _ -> []

staticStrategy
  :: Decls
  -> Name ('Tron 'Kernel)
  -> [Name ('Tron 'Buffer)]
  -- ^ Buffers whose current item must arrive before the kernel runs.
  -> [Name ('Tron 'Buffer)]
  -- ^ Buffers written by the kernel (for channel finish_writing_at).
  -> [Cpp.Statement]
  -- ^ Statements each helper runs before its first wait.
  -> IterationSpace
  -> KernelVariable
  -- ^ Kernel loop variable, bound to each item.
  -> (Locals -> [Cpp.Statement])
  -- ^ Body generator.
  -> Cpp.Statement
staticStrategy env name buffers_read buffers_written entry iterSpace loopvar bodyGen =
  Block $
    helperLaneSetup
      ++ entry
      ++ stripedLoop
        env
        name
        buffers_read
        buffers_written
        (ExprLit "*lane")
        iterSpace
        loopvar
        bodyGen

-- | The loop of the thread that runs lane @lane@ over the items of a
-- striped iteration space, with @tron::striped_loop@. For each item it waits
-- for the entry reads, runs the body with @loopvar@ bound to the item, and
-- publishes the writes.
stripedLoop
  :: Decls
  -> Name ('Tron 'Kernel)
  -> [Name ('Tron 'Buffer)]
  -- ^ Buffers whose current item must arrive before the kernel runs.
  -> [Name ('Tron 'Buffer)]
  -- ^ Buffers written by the kernel (for channel finish_writing_at).
  -> Expr
  -- ^ This thread's @tron::lane@.
  -> IterationSpace
  -> KernelVariable
  -- ^ Kernel loop variable, bound to each item.
  -> (Locals -> [Cpp.Statement])
  -- ^ Body generator.
  -> [Cpp.Statement]
stripedLoop env name buffers_read buffers_written lane iterSpace loopvar bodyGen =
  [ ExprStmt $
      FunCall
        "tron::striped_loop"
        [ LiteralExpr (StringLit (show name))
        , lane
        , items
        , channels buffers_read
        , channels buffers_written
        , Lambda
            [RefCaptureAll]
            [Param itemType cppLoopvar]
            (Block $ bodyGen $ insert (Locals M.empty) loopvar (Var cppLoopvar))
        ]
  ]
 where
  cppLoopvar = asCpp loopvar
  (items, itemType) = stripedItems iterSpace
  channels bufs =
    FunCall
      "std::tie"
      [MemberAccess "q_batch" (asCpp ch) | ch <- mapMaybe (channelName env) bufs]

-- | The items that a striped kernel over an iteration space deals out, in
-- order, and the C++ type of one item. A token kernel deals the batch's
-- tokens. See Note [Threads, stripes and lanes].
stripedItems :: IterationSpace -> (Expr, Type)
stripedItems = \case
  QBatchItems -> (MemberAccess "q_batch" "items", LiteralType "token_job_id")
  QBatchItemsExpertPairs{} -> error "stripedItems: QBatchItemsExpertPairs not supported"
  Fin _ -> error "stripedItems: Fin not supported"
  MoeEntries _ -> error "stripedItems: MoeEntries not yet supported"
  Singleton -> error "stripedItems: Singleton is a sync point, not iterable"

-- | Strategy for MoE body kernels: stripe the flat expert-major row sequence
-- across helpers without restarting worker assignment at expert boundaries.
-- Rows are grouped by ascending expert ID; matmul dispatch and completion may
-- follow a different order. See Note [Threads, stripes and lanes].
expertMajorStrategy
  :: Decls
  -> Name ('Tron 'Kernel)
  -- ^ Kernel name (for the trace event label).
  -> Name ('Tron 'MoeRouting)
  -- ^ Routing field named by QBatchItemsExpertPairs.
  -> Integer
  -- ^ Number of experts chosen per token (K).
  -> [Name ('Tron 'Buffer)]
  -- ^ Buffers whose current item must arrive before the kernel runs.
  -> [Name ('Tron 'Buffer)]
  -- ^ Buffers written by the kernel (for channel finish_writing_at).
  -> KernelVariable
  -- ^ Kernel loop variable name.
  -> (Locals -> [Cpp.Statement])
  -- ^ Body generator.
  -> Cpp.Statement
expertMajorStrategy env name routingName n_chosen buffers_read buffers_written loopvar bodyGen =
  Block $
    helperLaneSetup ++ [Block [traceEvent, loop]]
 where
  routingCpp = asCpp routingName
  cppLoopvar = asCpp loopvar
  expertMajor = MethodCall (Var routingCpp) "rows_in_expert_order" []
  channels = mapMaybe (channelName env) buffers_read
  written_channels = mapMaybe (channelName env) buffers_written

  -- The trace slice includes channel arrival latency, including the first row.
  traceEvent =
    ExprStmt $
      FunCall
        "TRACE_EVENT"
        [LiteralExpr (StringLit "model"), LiteralExpr (StringLit (show name))]

  loop =
    ForStmt
      (Declare (LiteralType "size_t") "row_ix" (Just (ExprLit "lane->ix")))
      (BinOp Lt (Var "row_ix") (MethodCall expertMajor "size" []))
      (IncAssignment (Var "row_ix") Add (ExprLit "lane->n"))
      $ Block
        ( [tsDecl]
            ++ map readChannel channels
            ++ bodyGen locals'
            ++ map (finishWritingAt (Var cppLoopvar)) written_channels
        )

  -- token_slot_id<K> ix = routing.rows_in_expert_order()[row_ix];
  tsDecl =
    Declare
      (TemplateType "token_slot_id" [LiteralType (show n_chosen)])
      cppLoopvar
      (Just (Index expertMajor (Var "row_ix")))

  locals' = insert (Locals M.empty) loopvar (Var cppLoopvar)

  readChannel ch =
    startReadingAt
      ( case channelIterSpace $ readDecl ch env of
          QBatchItems -> MethodCall (Var cppLoopvar) "token" []
          QBatchItemsExpertPairs{} -> Var cppLoopvar
          other -> error $ "expertMajorStrategy: unsupported input channel " ++ show other
      )
      ch

startReadingAt :: Expr -> Name ('Tron 'Channel) -> Cpp.Statement
startReadingAt arg name =
  ExprStmt $
    MethodCall (MemberAccess "q_batch" (asCpp name)) "start_reading_at" [arg]

-- | Helper function to @start_reading@ on a channel with a specific argument
startReading :: Expr -> Name ('Tron 'Channel) -> Cpp.Statement
startReading arg name =
  ExprStmt $
    MethodCall (MemberAccess "q_batch" (asCpp name)) "start_reading" [arg]

-- | Helper function for @start_writing@ on a channel with a specific argument
startWriting :: Expr -> Name ('Tron 'Channel) -> Cpp.Statement
startWriting arg name =
  ExprStmt $
    MethodCall (MemberAccess "q_batch" (asCpp name)) "start_writing" [arg]

-- | Helper function for @finish_reading@ on a channel with a specific argument
finishReading :: Expr -> Name ('Tron 'Channel) -> Cpp.Statement
finishReading arg name =
  ExprStmt $
    MethodCall (MemberAccess "q_batch" (asCpp name)) "finish_reading" [arg]

-- | Helper function for @finish_writing@ on a channel with a specific argument
finishWriting :: Expr -> Name ('Tron 'Channel) -> Cpp.Statement
finishWriting arg name =
  ExprStmt $
    MethodCall (MemberAccess "q_batch" (asCpp name)) "finish_writing" [arg]

-- | Helper function for @finish_writing_at@ on a channel with a specific argument
finishWritingAt :: Expr -> Name ('Tron 'Channel) -> Cpp.Statement
finishWritingAt arg name =
  ExprStmt $
    MethodCall (MemberAccess "q_batch" (asCpp name)) "finish_writing_at" [arg]

channelName :: Decls -> Name ('Tron 'Buffer) -> Maybe (Name ('Tron 'Channel))
channelName env buf = bufferGuardChannel $ readDecl buf env

-- | Wrap a C++ statement with an optional trace comment derived
-- from the Tron statement's provenance.
withTrace :: Tron.Statement -> Cpp.Statement -> [Cpp.Statement]
withTrace tronStmt cppStmt = withTraceStatements tronStmt [cppStmt]

-- | Prefix a statement sequence without introducing a C++ scope.
withTraceStatements :: Tron.Statement -> [Cpp.Statement] -> [Cpp.Statement]
withTraceStatements tronStmt cppStmts =
  let prov = stmtProvenance tronStmt
      comment = traceComment prov
   in if null comment
        then cppStmts
        else Cpp.Comment (drop 4 comment) : cppStmts

-- drop 4 removes leading " // " since Comment adds "//"

runStatement
  :: Decls
  -> M.Map MoeRouterId MoeRouterInfo
  -> MoeBlendNames
  -> M.Map AttentionOpId AttentionOperation
  -> Tron.Statement
  -> [Cpp.Statement]
runStatement env routers blendNames attentionById stmt = case stmt of
  MatmulFillStmt tensorName launcherName out inp _ ->
    withTrace stmt $
      ExprStmt $
        matmulFill env tensorName launcherName out inp
  MatmulPrepareStmt tensorName launcherName _ ->
    withTrace stmt $
      ExprStmt $
        matmulPrepare env tensorName launcherName
  MatmulLaunchStmt launcherName out (inp, consumerIdx) _ ->
    withTrace stmt $
      matmulLaunch env launcherName out inp consumerIdx
  HostStmt name _ ->
    withTrace stmt $
      ExprStmt $
        kernelCall (asCpp name) (LiteralExpr (IntLit 0))
  ChannelPrepareStmt name _ ->
    withTrace stmt $
      ExprStmt $
        channelPrepare name
  ChannelStartReadingStmt name _scope _ ->
    withTrace stmt $
      startReading (channelReadParticipant env name $ LiteralExpr $ IntLit 0) name
  ChannelFinishReadingStmt name _scope _ ->
    withTrace stmt $
      finishReading (channelReadParticipant env name $ LiteralExpr $ IntLit 0) name
  ChannelStartWritingStmt name _scope _ ->
    withTrace stmt $
      startWriting (LiteralExpr (IntLit 0)) name
  ChannelFinishWritingStmt name _scope _ ->
    withTrace stmt $
      finishWriting (LiteralExpr (IntLit 0)) name
  PrepareForLogitsStmt ->
    [ExprStmt $ MethodCall (Var "outer_state") "prepare_for_logits" []]
  PrepareAttentionStmt preparation ->
    case M.lookup (prepareAttentionOpId preparation) attentionById of
      Nothing ->
        error $
          "TronCpp: no attention operation for preparation "
            ++ show (prepareAttentionOpId preparation)
      Just operation -> withTrace stmt $ prepareAttentionOperation operation
  AttentionStmt attention -> withTraceStatements stmt $ submitAttentionOperation env attention
  MoeRouteStmt routingName indicesBuf routerId _ ->
    case M.lookup routerId routers of
      Nothing -> error $ "TronCpp: no MoE router " ++ show routerId
      Just router ->
        withTraceStatements stmt $
          moeRoute env routingName indicesBuf routerId (routerMatmuls router)
  MoeMatmulPrepareAndLaunchStmt operation ->
    case M.lookup (moeMatmulRouterId operation) routers of
      Nothing ->
        error $ "TronCpp: no MoE router " ++ show (moeMatmulRouterId operation)
      Just router ->
        withTrace stmt $ moeMatmulPrepareAndLaunch env (routerRouting router) operation
  MoeBlendStmt r w o i b lanes _ ->
    -- Dispatched through a lifted method so the early return in
    -- 'helperLaneSetup' exits the blend body, not @run()@.
    -- See Note [MoeBlend Method Lifting].
    withTrace stmt $
      ExprStmt $
        kernelCall (blendNames M.! MoeBlendKey r w o i b lanes) (LiteralExpr (IntLit 0))

runHelperStatement :: Decls -> MoeBlendNames -> Tron.Statement -> [Cpp.Statement]
runHelperStatement env blendNames stmt = case stmt of
  HostStmt name _ ->
    withTrace stmt $
      ExprStmt $
        kernelCall (asCpp name) (Var "worker_ix")
  MatmulFillStmt{} -> []
  MatmulPrepareStmt{} -> []
  MatmulLaunchStmt{} -> []
  ChannelPrepareStmt{} -> []
  ChannelStartReadingStmt name scope _ -> case scope of
    Tron.MainThreadOnly -> []
    Tron.AllWorkers ->
      withTrace stmt $
        startReading (channelReadParticipant env name $ Var "worker_ix") name
  ChannelFinishReadingStmt name scope _ -> case scope of
    Tron.MainThreadOnly -> []
    Tron.AllWorkers ->
      withTrace stmt $
        finishReading (channelReadParticipant env name $ Var "worker_ix") name
  ChannelStartWritingStmt name scope _ -> case scope of
    Tron.MainThreadOnly -> []
    Tron.AllWorkers ->
      withTrace stmt $
        startWriting (Var "worker_ix") name
  ChannelFinishWritingStmt name scope _ -> case scope of
    Tron.MainThreadOnly -> []
    Tron.AllWorkers ->
      withTrace stmt $
        finishWriting (Var "worker_ix") name
  PrepareForLogitsStmt -> []
  PrepareAttentionStmt _ -> []
  -- The helpers take part in the K store of a KV-writing operation. The main
  -- thread's save_k opens a window over the pass's tokens. The helpers are
  -- idle at this point of the schedule. Their next kernel waits for the
  -- attention output. The idle helpers claim work units of the window (runs
  -- of consecutive tokens inside one 16-token page block).
  -- Both sides call save_k at the same position of the statement list. Main
  -- passes worker index 0 (submitAttentionOperation). The helpers pass their
  -- own worker_ix. So the N-th window a helper enters in a pass is the N-th
  -- window main opens in that pass.
  -- See Note [Shared block save] in model.hpp. Operations without a KV write
  -- emit nothing here.
  AttentionStmt attention -> case attentionKvWrite attention of
    Nothing -> []
    Just kvWrite ->
      withTrace stmt $
        attentionRuntimeCall
          "save_k"
          attention
          [Var $ asCpp $ attentionKey kvWrite, Var "worker_ix", Var "n_workers"]
  MoeRouteStmt{} -> []
  MoeMatmulPrepareAndLaunchStmt{} -> []
  MoeBlendStmt r w o i b lanes _ ->
    -- Dispatch into the lifted blend method, just like HostStmt.
    -- See Note [MoeBlend Method Lifting].
    withTrace stmt $
      ExprStmt $
        kernelCall (blendNames M.! MoeBlendKey r w o i b lanes) (Var "worker_ix")

-- | The separate hoistable statement always advances the operation phase, but
-- the C++ executor performs HW preparation there only for the early policy.
-- See Note [Early and late hardware attention launch] in model.hpp. The statement
-- resolves its explicit query buffer from the paired operation.
prepareAttentionOperation :: AttentionOperation -> Cpp.Statement
prepareAttentionOperation stmt =
  attentionRuntimeCall
    "prepare_attention_job"
    stmt
    [Var $ asCpp $ attentionQuery stmt]

-- | Launch prepared hardware work before current-token K/V saves for large
-- batches. For small batches, prepare and launch after the saves. The runtime
-- wrappers own the batch-size heuristic, keeping policy out of the Tron IR. See
-- Note [Early and late hardware attention launch] in model.hpp.
submitAttentionOperation :: Decls -> AttentionOperation -> [Cpp.Statement]
submitAttentionOperation env stmt =
  [earlyLaunch]
    ++ maybe [] saveKv (attentionKvWrite stmt)
    ++ [latePrepare, lateLaunch]
 where
  earlyLaunch =
    attentionRuntimeCall
      "launch_early_hw_attention"
      stmt
      [ Var $ asCpp $ attentionQuery stmt
      , MemberAccess
          (Var "q_batch")
          (asCpp $ attentionChannel env $ attentionQuery stmt)
      ]
  latePrepare =
    attentionRuntimeCall
      "prepare_late_hw_attention"
      stmt
      [Var $ asCpp $ attentionQuery stmt]
  lateLaunch =
    attentionRuntimeCall
      "launch_late_hw_attention"
      stmt
      [ Var $ asCpp $ attentionQuery stmt
      , MemberAccess
          (Var "q_batch")
          (asCpp $ attentionChannel env $ attentionQuery stmt)
      ]
  saveKv kvWrite =
    [ startOperand $ attentionChannel env $ attentionKey kvWrite
    , -- Main is worker 0, as in kernelCall. n_workers (main + main helpers) is
      -- in scope in run(). It lets save_k share the K store with the helpers'
      -- save_k calls (runHelperStatement).
      attentionRuntimeCall
        "save_k"
        stmt
        [Var $ asCpp $ attentionKey kvWrite, LiteralExpr (IntLit 0), Var "n_workers"]
    , startOperand $ attentionChannel env $ attentionValue kvWrite
    , attentionRuntimeCall
        "save_v"
        stmt
        [Var $ asCpp $ attentionValue kvWrite]
    ]
  startOperand channel =
    ForStmt "size_t task_ix = 0" "task_ix < q_batch->items.size()" "task_ix++" $
      Block [startReadingAt "task_ix" channel]

attentionChannel :: Decls -> Name ('Tron 'Buffer) -> Name ('Tron 'Channel)
attentionChannel env buffer =
  fromMaybe
    (error $ "TronCpp: attention buffer has no guard channel: " ++ show buffer)
    (channelName env buffer)

-- | Invoke the runtime with an ingest-known geometry and operation index.
attentionRuntimeCall :: Name Cpp -> AttentionOperation -> [Expr] -> Cpp.Statement
attentionRuntimeCall method stmt args =
  ExprStmt $
    TemplateMethodCall
      (Var "outer_state")
      method
      (attentionOperationTemplateArgs stmt)
      (ExprLit "q_batch->outer_batch" : args)

matmulFill
  :: Decls
  -> Name ('Tron 'Tensor)
  -> Name ('Tron 'Launcher)
  -> Name ('Tron 'Buffer)
  -> Name ('Tron 'Buffer)
  -> Expr
matmulFill env tensorName launcherName out inp = FunCall fname args
 where
  args =
    [ Var $ asCpp out
    , Var $ asCpp inp
    , items
    , launcher
    , waitable
    , LiteralExpr (StringLit $ show tensorName)
    ]
  fname = NamespacedFun (tensorType ti) "fill_matmul_template"
  ti = readDecl tensorName env
  items = MemberAccess "q_batch" "items"
  launcher = MemberAccess "q_batch" $ asCpp launcherName
  inp_channel =
    expectJust
      ("TronCpp.matmulFill: matmul input buffer has no guard channel:" PP.<+> PP.pretty inp)
      (bufferGuardChannel $ readDecl inp env)
  waitable = MethodCall (MemberAccess "q_batch" $ asCpp inp_channel) "waitable" []

matmulPrepare :: Decls -> Name ('Tron 'Tensor) -> Name ('Tron 'Launcher) -> Expr
matmulPrepare _ tensorName launcherName = MethodCall weight "prepare_matmul" [launcher]
 where
  -- TODO: Think through layer support; maybe something like this?
  -- weight = MemberAccess (Index (Var "model") (Var "layer")) name
  weight = FieldRef "model" $ asCpp tensorName
  launcher = MemberAccess "q_batch" $ asCpp launcherName

matmulLaunch
  :: Decls
  -> Name ('Tron 'Launcher)
  -> Name ('Tron 'Channel)
  -> Name ('Tron 'Channel)
  -> MatrixConsumerIndex
  -> Cpp.Statement
matmulLaunch _ launcherName outChannel inp_channel (MatrixConsumerIndex consumerIdx) =
  Block $ [write, read] ++ countMatrixCallback ++ [launch]
 where
  write = startWriting (LiteralExpr (IntLit 0)) outChannel
  read = startReading (LiteralExpr (IntLit $ fromIntegral consumerIdx)) inp_channel
  launch = ExprStmt $ MethodCallViaPtr "q_batch" (asCpp launcherName) [callback]
  callback =
    matrixCallback
      [ finishWriting (LiteralExpr (IntLit 0)) outChannel
      , finishReading (LiteralExpr (IntLit $ fromIntegral consumerIdx)) inp_channel
      ]

-- | Count a matmul launch on the batch's @matrix_callbacks@ latch. These
-- statements precede the launch, so that a callback the launch runs
-- synchronously is counted. See Note [Matrix callback lifetime] in
-- h/tron/models/common.hpp.
countMatrixCallback :: [Cpp.Statement]
countMatrixCallback =
  [ LitStmt "latch_ref callbacks_done = q_batch->outer_batch->matrix_callbacks;"
  , LitStmt "++callbacks_done;"
  ]

-- | A matmul completion callback that runs @body@ and then retires itself on
-- the latch counted by 'countMatrixCallback'. The count-down is its last
-- statement: the batch may be destroyed as soon as it lands.
matrixCallback :: [Cpp.Statement] -> Expr
matrixCallback body =
  Lambda [CopyCapture "q_batch", CopyCapture "callbacks_done"] [] $
    Block (body ++ [LitStmt "callbacks_done.count_down();"])

-- | Generate code for MoeRouteStmt: rebuild routing in place from pre-computed
-- indices, applying any model-level routing override. Persistent routing buffers
-- retain capacity across forward passes. Then build the router's matmul schedule and
-- record per-(router, expert) token counts. See Note [MoE Expert Routing Stats]
-- in h/tron/models/expert_stats.hpp.
moeRoute
  :: Decls
  -> Name ('Tron 'MoeRouting)
  -> Name ('Tron 'Buffer)
  -> MoeRouterId
  -> [MoeMatmulOperation]
  -> [Cpp.Statement]
moeRoute env routingName indicesBuf routerId matmuls =
  case channelName env indicesBuf of
    Just ch ->
      [ ForStmt
          "size_t task_ix = 0"
          "task_ix < q_batch->items.size()"
          "task_ix++"
          $ Block [startReadingAt "task_ix" ch]
      , ExprStmt $
          TemplateFunCall
            "build_moe_routing_from_indices"
            [ ExprType (LiteralExpr (IntLit $ fromIntegral n))
            , ExprType (LiteralExpr (IntLit $ fromIntegral k))
            ]
            [ Var $ asCpp indicesBuf
            , Var $ derivedCppName routingName "per_token"
            , MemberAccess "q_batch" "items"
            , FunCall
                "expert_routing_override_for"
                [ routingOverride
                , moeRouterIdExpr routerId
                ]
            , Var $ asCpp routingName
            ]
      , Assignment
          (Var $ moeScheduleName routerId)
          ( FunCall
              "make_expert_matmul_schedule"
              ( Var (asCpp routingName)
                  : map (FieldRef "model" . asCpp . moeMatmulTensor) matmuls
              )
          )
      , ExprStmt $
          MethodCall
            (FieldRef (FieldRef (Var "outer_state") "model_ref") "expert_stats_")
            "record_router"
            [ moeRouterIdExpr routerId
            , Var $ asCpp routingName
            ]
      ]
    Nothing ->
      error $ "MoeRouteStmt: no channel for indices: " ++ show indicesBuf
 where
  ri = readDecl routingName env
  n = moeRoutingNumExperts ri
  k = moeRoutingTopK ri
  modelRef = FieldRef (Var "outer_state") "model_ref"
  routingOverride = FieldRef modelRef "expert_routing_override_"

-- | Generate code for MoeMatmulPrepareAndLaunchStmt: call
-- @expert_weights::prepare_and_launch@, which per-expert fills the matmul
-- template, reserves hardware slots, and fires the launcher in a single
-- pass. Wraps QBatchItems-indexed input in @token_slot_view@ when needed.
-- See Note [MoE Lowering Strategy] in TypedFxBulk.hs.
moeMatmulPrepareAndLaunch
  :: Decls -> Name ('Tron 'MoeRouting) -> MoeMatmulOperation -> Cpp.Statement
moeMatmulPrepareAndLaunch env routingName operation =
  Block $
    maybeView
      ++ [ write
         , read
         ]
      ++ countMatrixCallback
      ++ [prepareAndLaunch]
 where
  MoeMatmulOperation
    { moeMatmulTensor = tensorName
    , moeMatmulLauncher = launcherName
    , moeMatmulRouterId = routerId
    , moeMatmulId = matmulId
    , moeMatmulOutput = outBuf
    , moeMatmulInput = inBuf
    , moeMatmulOutputChannel = outChannel
    , moeMatmulInputChannel = (inpChannel, MatrixConsumerIndex consumerIdx)
    } = operation
  ri = readDecl routingName env
  k = moeRoutingTopK ri
  ti = readDecl tensorName env
  -- Per-expert shape: strip the expert dimension (first) from 3D shape.
  -- Weight is [outDim, inDim]; prepare_and_launch wants <in_dim, out_dim>.
  (outDim, inDim) = case drop 1 (shape ti) of
    [o, i] -> (o, i)
    s -> error $ "moeMatmulPrepareAndLaunch: expected 2D per-expert shape, got " ++ show s
  inBufInfo = readDecl inBuf env
  needsView = bufferIterSpace inBufInfo == QBatchItems
  viewName = derivedCppName inBuf "view"
  inputExpr = if needsView then Var viewName else Var $ asCpp inBuf
  -- token_slot_view<K, btensor_t<width>> inBuf_view{inBuf};
  maybeView
    | needsView =
        [ DeclareBraceInit
            ( TemplateType
                "token_slot_view"
                [ ExprType (LiteralExpr (IntLit $ fromIntegral k))
                , TemplateType "btensor_t" [ExprType $ bufferWidth inBufInfo]
                ]
            )
            viewName
            (Var $ asCpp inBuf)
        ]
    | otherwise = []
  -- If the input buffer has a guard channel, pass its readiness layout. The
  -- channel's waitable follows its item list, which channelItemsArg builds from
  -- the same iteration space.
  maybeWaitable = case channelName env inBuf of
    Just ch ->
      [ activationReady (channelIterSpace (readDecl ch env)) $
          MethodCall (MemberAccess "q_batch" $ asCpp ch) "waitable" []
      ]
    Nothing -> []
  activationReady iterSpace waitable = case iterSpace of
    QBatchItems ->
      BraceInit
        (LiteralType "token_major_activation_ready")
        [waitable]
    QBatchItemsExpertPairs _ channelK
      | channelK /= toInteger k ->
          error $
            "moeMatmulPrepareAndLaunch: guard channel top_k "
              ++ show channelK
              ++ " differs from routing top_k "
              ++ show k
      | otherwise ->
          BraceInit
            ( TemplateType
                "token_slot_major_activation_ready"
                [ExprType (LiteralExpr (IntLit channelK))]
            )
            [waitable]
    s ->
      error $
        "moeMatmulPrepareAndLaunch: no activation readiness layout for guard channel "
          ++ "iteration space "
          ++ show s
  write = startWriting (LiteralExpr (IntLit 0)) outChannel
  read = startReading (LiteralExpr (IntLit $ fromIntegral consumerIdx)) inpChannel
  prepareAndLaunch =
    ExprStmt $
      TemplateMethodCall
        (FieldRef "model" $ asCpp tensorName)
        "prepare_and_launch"
        [ExprType inDim, ExprType outDim]
        ( [ MemberAccess "q_batch" $ asCpp launcherName
          , Var $ asCpp routingName
          , MethodCall
              (Var $ moeScheduleName routerId)
              "jobs_for"
              [BraceInit "expert_matmul_id" [LiteralExpr $ IntLit $ unExpertMatmulId matmulId]]
          , inputExpr
          , Var $ asCpp outBuf
          , callback
          ]
            ++ maybeWaitable
        )
  callback =
    matrixCallback
      [ finishWriting (LiteralExpr (IntLit 0)) outChannel
      , finishReading (LiteralExpr (IntLit $ fromIntegral consumerIdx)) inpChannel
      ]

-- Note [MoeBlend Method Lifting]
-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
-- MoeBlendStmt is lifted into a dedicated method on @state@, mirroring how
-- HostStmt dispatches into kernel methods. The reason is the early return on
-- a thread with no lane of the blend's stripe ('helperLaneSetup' and
-- 'alignedLaneMethods'; see Note [Threads, stripes and lanes]): if a body from
-- 'moeBlendMethods' is inlined into @run()@ or @run_main_help()@ directly, the
-- @return@ exits the enclosing forward-pass method instead of just the blend
-- body, dropping every subsequent layer.
--
-- The lifting deduplicates by ('MoeBlendKey'), so identical blends across
-- layers share a single generated method. Names are @moe_blend_<i>@ in
-- order of first appearance in @run@. An aligned-lane blend's lane method is
-- @moe_blend_<i>_lane@.
data MoeBlendKey
  = MoeBlendKey
      (Name ('Tron 'MoeRouting))
      (Name ('Tron 'Buffer))
      -- ^ blend weights
      (Name ('Tron 'Buffer))
      -- ^ output
      (Name ('Tron 'Buffer))
      -- ^ input
      (Maybe (Name ('Tron 'ExpertView)))
      -- ^ optional fused bias source
      KernelLanes
  deriving (Eq, Ord, Show)

moeBlendStmtKey :: Tron.Statement -> Maybe MoeBlendKey
moeBlendStmtKey (MoeBlendStmt r w o i b lanes _) = Just (MoeBlendKey r w o i b lanes)
moeBlendStmtKey _ = Nothing

-- | Unique MoeBlend operations in order of first appearance, paired with the
-- generated method name. See Note [MoeBlend Method Lifting].
collectMoeBlends :: [Tron.Statement] -> [(MoeBlendKey, Name Cpp)]
collectMoeBlends stmts =
  zipWith (\k i -> (k, fromString ("moe_blend_" ++ show i))) uniqueKeys [0 :: Int ..]
 where
  uniqueKeys = preserveOrderNub (mapMaybe moeBlendStmtKey stmts)
  preserveOrderNub = go S.empty
   where
    go _ [] = []
    go seen (x : xs)
      | S.member x seen = go seen xs
      | otherwise = x : go (S.insert x seen) xs

-- | Lookup table from blend key to generated method name.
type MoeBlendNames = M.Map MoeBlendKey (Name Cpp)

moeBlendNames :: [Tron.Statement] -> MoeBlendNames
moeBlendNames = M.fromList . collectMoeBlends

-- | Generate the methods that perform one lifted MoeBlend. Parameter list
-- matches kernel methods so 'kernelCall' dispatches uniformly. An aligned-lane
-- blend also gets a lane method. See Note [MoeBlend Method Lifting] and
-- Note [Aligned lane domain].
moeBlendMethods :: Decls -> (MoeBlendKey, Name Cpp) -> [Method]
moeBlendMethods env (MoeBlendKey r w o i b lanes, name) = case lanes of
  HelperStripe ->
    [ Method "void" name kernelParams [] $
        Cpp.block [staticStrategy env "moe_blend" [w] [o] [] QBatchItems "tok" body]
    ]
  AlignedLanes ->
    alignedLaneMethods name False $
      stripedLoop env "moe_blend" [w] [o] (Var "lane") QBatchItems "tok" body
 where
  body = moeBlendBody env r w o i b

-- | The body of a MoeBlendStmt for token @tok@, which blends per-expert
-- results. When 'mBias' is Just, it emits the fused 'blend_with_bias_expr',
-- which folds a per-expert bias add into the weighted accumulation. See
-- Note [MoeRouter Bias Lifting] in h/tron/models/mixture_of_experts.hpp.
moeBlendBody
  :: Decls
  -> Name ('Tron 'MoeRouting)
  -> Name ('Tron 'Buffer)
  -> Name ('Tron 'Buffer)
  -> Name ('Tron 'Buffer)
  -> Maybe (Name ('Tron 'ExpertView))
  -> Locals
  -> [Cpp.Statement]
moeBlendBody env routingName blendWeightsBuf outBuf inBuf mBias _ =
  perSlotSync
    ++
    -- output[tok] = blend[_with_bias]_expr<...>(tok, weights[tok], input[, bias])
    [ Assignment
        (Index (Var $ asCpp outBuf) (Var "tok"))
        ( TemplateFunCall
            blendFun
            blendTemplateArgs
            blendCallArgs
        )
    ]
 where
  ri = readDecl routingName env
  k = moeRoutingTopK ri
  outWidth = bufferWidth (readDecl outBuf env)
  baseTemplateArgs =
    [ ExprType outWidth
    , ExprType (LiteralExpr (IntLit $ fromIntegral k))
    , TemplateType "btensor_t" [ExprType outWidth]
    ]
  baseCallArgs =
    [ Var "tok"
    , Index (Var $ asCpp blendWeightsBuf) (Var "tok")
    , Var $ asCpp inBuf
    ]
  (blendFun, blendTemplateArgs, blendCallArgs) = case mBias of
    Nothing -> ("blend_expr", baseTemplateArgs, baseCallArgs)
    Just evName ->
      ( "blend_with_bias_expr"
      , baseTemplateArgs ++ [DecltypeType (Var $ asCpp evName)]
      , baseCallArgs ++ [Var $ asCpp evName]
      )
  -- Per-slot channel sync by typed token_slot_id.
  -- With bias fusion, we read from the unbiased matmul output's channel
  -- (inBuf is the matmul output) and the bias source needs no per-slot
  -- sync (it's an ExpertView resolved at construction time).
  perSlotSync = case channelName env inBuf of
    Just ch ->
      [ serialStrategy $
          resolveIterationSpace
            env
            "slot"
            (Fin (Static $ fromIntegral k))
            ( const
                [ startReadingAt
                    ( TemplateFunCall
                        "token_slot_id"
                        [ExprType (LiteralExpr (IntLit $ fromIntegral k))]
                        [Var "tok", FunCall "slot_id" [Var "slot"]]
                    )
                    ch
                ]
            )
            (Locals M.empty)
      ]
    Nothing -> []

kernelCall :: Name Cpp -> Expr -> Expr
kernelCall name worker_ix =
  -- Can add Var "layer" (in the second position) when we do layer abstraction.
  FunCall (NamedFun name) [Var "q_batch", worker_ix, Var "n_workers"]

channelPrepare :: Name ('Tron 'Channel) -> Expr
channelPrepare name = MethodCall (MemberAccess "q_batch" (asCpp name)) "prepare" []

-- | Map a host worker into a channel's logical consumer participant space.
-- See Note [Mixed parallel and matrix consumers] in Tron.hs.
channelReadParticipant :: Decls -> Name ('Tron 'Channel) -> Expr -> Expr
channelReadParticipant env name worker =
  case (consumerMatrixCount consumer, consumerHasHostStripe consumer) of
    (Just n, True) -> offset n worker
    _ -> worker
 where
  consumer = channelConsumer $ readDecl name env
  -- A normalized mixed contract has a positive matrix count.
  offset n (LiteralExpr (IntLit 0)) = LiteralExpr $ IntLit $ fromIntegral n
  offset n participant = LiteralExpr (IntLit $ fromIntegral n) `plus` participant

-- | C++ tensor type name for a given scalar type.
scalarTensorTypeName :: ScalarType -> Type
scalarTensorTypeName RealScalar = LiteralType "btensor_t"
scalarTensorTypeName IntScalar = LiteralType "itensor_t"

-- | C++ type for a buffer: indexed_vector<indexType, btensor_t<width>>
bufferType :: ScalarType -> IterationSpace -> Expr -> Type
bufferType scalarTy iterSpace width =
  TemplateType
    "indexed_vector"
    [ iterSpaceIndexType iterSpace
    , TemplateType (scalarTensorTypeName scalarTy) [ExprType width]
    ]

-- | C++ index type for an iteration space.
iterSpaceIndexType :: IterationSpace -> Type
iterSpaceIndexType QBatchItems = LiteralType "token_job_id"
iterSpaceIndexType (Fin _) = LiteralType "size_t"
iterSpaceIndexType (QBatchItemsExpertPairs _ n_chosen) =
  TemplateType "token_slot_id" [LiteralType $ show n_chosen]
iterSpaceIndexType (MoeEntries _) = error "iterSpaceIndexType: MoeEntries not yet supported"
iterSpaceIndexType Singleton = LiteralType "singleton_id"

-- | Generates the batch struct definition including fields, constructor, and reset_channels method.
batchPluginStruct :: String -> Module -> StructDef
batchPluginStruct implName m@Module{modDecls = env} =
  StructDef "plugin_batch" [] components
 where
  lanes = hasAlignedLanes m
  components =
    [outer_batch_field, items_field]
      ++ expertPairFields
      ++ channel_fields
      ++ launcherFields
      ++ attentionLanesField
      ++ [constructor, resetMethod]
  attentionLanesField =
    [ LiteralDef "// See Note [Aligned lane domain] in ingest/src/TronCpp.hs."
    | lanes
    ]
      ++ [LiteralDef "size_t n_attention_lanes = 0;" | lanes]
  items_field = LiteralDef "std::vector<token_job_id>& items;"
  outer_batch_field = LiteralDef $ "batch<::tron::model<" ++ implName ++ ">>* outer_batch;"
  channel_fields = map (FieldDef . channelField) $ getChannels env
  launcherFields = map (FieldDef . launcherField) $ getLaunchers env
  constructor =
    ConstructorDef $
      Constructor
        "plugin_batch"
        constructorParams
        initializers
        (Block [])
  resetMethod = MethodDef $ resetChannelsMethod lanes env
  constructorParams =
    [ Param "state&" "state"
    , Param "auto&" "outer_batch"
    , Param "latch_arena&" "latches"
    , Param "size_t" "ix"
    ]
  initializers =
    [ Initializer "outer_batch" [AddrOf (Var "outer_batch")]
    , Initializer "items" [ExprLit "outer_batch.items"]
    ]
      ++ expertPairInitializers
      ++ map (channelInitializer env) (getChannels env)
  -- Collect distinct top_k values from QBatchItemsExpertPairs channels
  expertPairTopKs =
    List.nub
      [ k
      | (_, ci) <- getChannels env
      , QBatchItemsExpertPairs _ k <- [channelIterSpace ci]
      ]
  -- For each distinct top_k, declare a field and initializer
  expertPairFields =
    [ LiteralDef $
        "std::vector<token_slot_id<" ++ show k ++ ">> " ++ expertPairItemsName k ++ ";"
    | k <- expertPairTopKs
    ]
  expertPairInitializers =
    [ Initializer
        (fromString $ expertPairItemsName k)
        [FunCall (fromString $ "expand_expert_pairs<" ++ show k ++ ">") [Var "items"]]
    | k <- expertPairTopKs
    ]

-- | Generates the reset_channels method definition. With aligned lanes it
-- first asserts that the helpers and attention workers fill the pool. It then
-- decides whether the attention workers join the aligned lane domain in this
-- pass. See Note [Aligned lane domain].
resetChannelsMethod :: Bool -> Decls -> Method
resetChannelsMethod lanes env = Method "void" "reset_channels" params [] body
 where
  params = [Param "size_t" "n_attn_workers", Param "size_t" "n_workers"]
  body = Block $ attentionLanes ++ map generateResetCall (getChannels env)
  attentionLanes
    | lanes =
        [ Cpp.Comment "See Note [Aligned lane domain] in ingest/src/TronCpp.hs."
        , LitStmt $
            List.intercalate
              "\n"
              [ "TRON_ASSERT(n_workers - 1 + n_attn_workers =="
              , "    app_pool().num_workers(),"
              , "    \"helpers and attention workers must fill the pool; \""
              , "    \"see Note [Attention workers are the last pool workers]\");"
              ]
        , LitStmt $
            "n_attention_lanes = tron::is_large_pass(items.size(), n_workers) "
              ++ "? n_attn_workers : 0;"
        ]
    | otherwise = []

-- | Generates a single channel.reset(producerCount, consumerCount) call statement.
generateResetCall :: (Name ('Tron 'Channel), ChannelInfo) -> Cpp.Statement
generateResetCall (name, ChannelInfo{channelProducer = producer, channelConsumer = consumer}) =
  ExprStmt $ MethodCall (Var $ asCpp name) "reset" [producerCount, consumerCount]
 where
  -- The lane side of a lane channel: main and the helpers, plus the attention
  -- workers in passes where they join the aligned lane domain.
  laneCount = Var "n_workers" `plus` Var "n_attention_lanes"
  producerCount = case producer of
    MatrixP _ _ -> LiteralExpr (IntLit 1)
    MoeMatrixP{} -> LiteralExpr (IntLit 1)
    ParP _ -> Var "n_workers"
    LaneP _ -> laneCount
    WorkerP AttentionWorkers -> Var "n_attn_workers"
    MoeRoutingP -> LiteralExpr (IntLit 1) -- Worker 0 rebuilds routing in place
  consumerCount =
    case consumerHostStripes consumer of
      (lanes, _) : _ ->
        let hostCount = case lanes of
              HelperStripe -> Var "n_workers"
              AlignedLanes -> laneCount
         in case consumerMatrixCount consumer of
              Just n -> LiteralExpr (IntLit $ fromIntegral n) `plus` hostCount
              Nothing -> hostCount
      [] -> case consumerDomains consumer of
        domain NE.:| [] -> domainCount domain
        _ -> error $ "unsupported consumer domains: " ++ show consumer
  domainCount :: ConsumerDomain k -> Expr
  domainCount domain = case domain of
    MatrixConsumer n -> LiteralExpr (IntLit $ fromIntegral n)
    ParConsumer _ -> Var "n_workers"
    LaneConsumer _ -> laneCount
    SingleHostConsumer -> LiteralExpr (IntLit 1) -- Single main-thread consumer
    WorkerConsumer AttentionWorkers -> Var "n_attn_workers"
    MoeRoutingConsumer -> Var "n_workers" -- All workers block at start_reading until routing is rebuilt

-- Helper functions for reference buffer handling

-- Determine if a buffer should be a reference and what it should reference
referenceBuffer :: Module -> Name ('Tron 'Buffer) -> Maybe Expr
referenceBuffer Module{result = resultBuf} bufferName
  | bufferName == resultBuf = Just $ FieldRef (Var "outer_state") "final_embedding"
  | otherwise = Nothing

-- | Generate state fields for an MoE routing object.
-- moe_routing holds a pointer to per_token data, so we need two fields:
--   indexed_vector<token_job_id, indexed_vector<slot_id, expert_id>> routingName_per_token;
--   moe_routing<N, K> routingName;
-- The routing is filled in place by build_moe_routing_from_indices each pass,
-- so its buffers retain capacity across passes.
moeRoutingFields :: (Name ('Tron 'MoeRouting), MoeRoutingInfo) -> [Field]
moeRoutingFields (name, MoeRoutingInfo{moeRoutingNumExperts = n, moeRoutingTopK = k}) =
  [ Field perTokenType (derivedCppName name "per_token")
  , Field routingType (asCpp name)
  ]
 where
  perTokenType =
    TemplateType
      "indexed_vector"
      [ LiteralType "token_job_id"
      , TemplateType "indexed_vector" [LiteralType "slot_id", LiteralType "expert_id"]
      ]
  routingType =
    TemplateType
      "moe_routing"
      [ ExprType (LiteralExpr (IntLit $ fromIntegral n))
      , ExprType (LiteralExpr (IntLit $ fromIntegral k))
      ]

-- Generate one schedule per logical router from its matmul occurrences.
moeScheduleField :: Decls -> MoeRouterId -> MoeRouterInfo -> Field
moeScheduleField env routerId info =
  Field
    ( TemplateType
        "router_expert_matmul_schedule"
        [ ExprType $ LiteralExpr $ IntLit $ fromIntegral n
        , ExprType $ LiteralExpr $ IntLit $ fromIntegral $ length $ routerMatmuls info
        ]
    )
    (moeScheduleName routerId)
 where
  n = moeRoutingNumExperts $ readDecl (routerRouting info) env

-- Generate expert_slot_view state field.
expertViewFields :: (Name ('Tron 'ExpertView), ExpertViewInfo) -> [Field]
expertViewFields (name, ExpertViewInfo{evNumExperts = n, evTopK = k, evTensorName = tensor}) =
  [Field viewType (asCpp name)]
 where
  viewType =
    TemplateType
      "expert_slot_view"
      [ ExprType (LiteralExpr (IntLit $ fromIntegral n))
      , ExprType (LiteralExpr (IntLit $ fromIntegral k))
      , LiteralType $
          "decltype("
            ++ show (PP.pretty (FieldRef (Var "model") (asCpp tensor)))
            ++ ")"
      ]

-- Generate constructor initializer for expert_slot_view: {routing, model.param}.
-- The routing is a reference to the moe_routing that is filled in place each pass.
expertViewInitializer :: (Name ('Tron 'ExpertView), ExpertViewInfo) -> Cpp.Initializer
expertViewInitializer
  (name, ExpertViewInfo{evRoutingName = routing, evTensorName = tensor}) =
    Initializer (asCpp name) [Var (asCpp routing), FieldRef (Var "model") (asCpp tensor)]

-- Generate appropriate field type for buffers
bufferField :: Module -> (Name ('Tron 'Buffer), BufferInfo) -> Field
bufferField mod (name, bufInfo) = Field fieldType (asCpp name)
 where
  baseType = bufferType (bufferScalarType bufInfo) (bufferIterSpace bufInfo) (bufferWidth bufInfo)
  fieldType = case referenceBuffer mod name of
    Just _ -> ReferenceType baseType
    Nothing -> baseType

-- Generate appropriate field type for channels
channelField :: (Name ('Tron 'Channel), ChannelInfo) -> Field
channelField (name, channelInfo) = Field baseType $ asCpp name
 where
  baseType =
    TemplateType
      "channel"
      [iterSpaceIndexType (channelIterSpace channelInfo), bufTy, latch_ty]
  bufTy =
    TemplateType
      (scalarTensorTypeName $ channelScalarType channelInfo)
      [ExprType (channelWidth channelInfo)]
  latch_ty = TemplateType "tensor_latch" [realProdTy]
  -- See Note [Tensor latch synchronization].
  prodTy = case channelProducer channelInfo of
    MatrixP shape memSpace -> tensorTypeFromShapeAndSpace shape memSpace
    -- See Note [Expert matmuls]
    MoeMatrixP shape nExperts memSpace ->
      TemplateType
        "expert_weights"
        [ expertTensorTypeFromShapeAndSpace shape memSpace
        , ExprType (LiteralExpr (IntLit (fromIntegral nExperts)))
        ]
    ParP _ -> "signaled_producer_t"
    LaneP _ -> "signaled_producer_t"
    WorkerP AttentionWorkers -> "fallback_producer_t"
    MoeRoutingP -> "fallback_producer_t" -- Sync-only channel; see Note [MoeRouting Channel]
  realProdTy = case channelConsumer channelInfo of
    WorkerC AttentionWorkers -> "fallback_producer_t"
    _ -> prodTy

-- Generate reference initializers for buffers
referenceBufferInitializer
  :: Module -> (Name ('Tron 'Buffer), BufferInfo) -> Maybe Initializer
referenceBufferInitializer mod (bufName, _) =
  case referenceBuffer mod bufName of
    Just ref_expr -> Just $ Initializer (asCpp bufName) [ref_expr]
    Nothing -> Nothing

-- Note [Channel Initialization and Iteration Spaces]
-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
-- The channel constructor receives an "items" argument that maps
-- iteration-space indices to latch positions. For QBatchItems, this
-- is the batch items vector (q_batch->items), and the channel
-- internally repeats the task→token_job_id mapping when generated code
-- calls start_reading_at(task) with a task position. This is the same
-- mapping that resolveIterationSpace performs when remapping the loop
-- variable. These two sites must agree; if new iteration spaces are added,
-- both the channel initialization and resolveIterationSpace need
-- corresponding updates. Striped kernels pass the item itself
-- ('stripedItems').
--
-- For QBatchItemsExpertPairs(K), the items vector is a
-- std::vector<token_slot_id<K>> built by expand_expert_pairs<K>
-- from the token items. Each distinct K gets its own field on
-- plugin_batch (e.g., expert_items_2), declared and initialized
-- in batchPluginStruct.
--

-- | Generates an initializer for a channel field in the batch constructor.
channelInitializer :: Decls -> (Name ('Tron 'Channel), ChannelInfo) -> Initializer
channelInitializer env (name, channelInfo) =
  case channelProducer channelInfo of
    MoeRoutingP ->
      -- Sync-only channel; share the dummy buffer/items fixtures
      -- on state. See Note [MoeRouting Channel] in Tron.hs.
      Initializer
        (asCpp name)
        [ FieldRef (Var "state") "_routing_sync_buf"
        , FieldRef (Var "state") "_singleton_items"
        , Var "latches"
        , LiteralExpr (StringLit (show name))
        , Var "ix"
        ]
    _ ->
      let bufferName = findBufferForChannel env name
       in Initializer
            (asCpp name)
            [ FieldRef (Var "state") $ asCpp bufferName
            , channelItemsArg (channelIterSpace channelInfo)
            , Var "latches"
            , LiteralExpr (StringLit (show bufferName))
            , Var "ix"
            ]

-- | The items argument for channel initialization.
-- See Note [Channel Initialization and Iteration Spaces].
channelItemsArg :: IterationSpace -> Expr
channelItemsArg QBatchItems = Var "items"
channelItemsArg (QBatchItemsExpertPairs _ k) = Var $ fromString $ expertPairItemsName k
channelItemsArg (Fin _) = error "channelItemsArg: Fin iteration space channels not yet supported"
channelItemsArg (MoeEntries _) = error "channelItemsArg: MoeEntries channels not yet supported"
channelItemsArg Singleton = error "channelItemsArg: Singleton iteration spaces should be dealt with elsewhere"

-- | Field name for the expert-pair items vector for a given top_k.
expertPairItemsName :: Integer -> String
expertPairItemsName k = "expert_items_" ++ show k

-- Placeholder: Finds the buffer associated with a channel.
-- This needs a robust implementation based on how buffers and channels are actually linked.
findBufferForChannel :: Decls -> Name ('Tron 'Channel) -> Name ('Tron 'Buffer)
findBufferForChannel env channelName =
  case List.find (\(_, bi) -> bufferGuardChannel bi == Just channelName) (getBuffers env) of
    Just (bufferName, _) -> bufferName
    Nothing -> error $ "Cannot find buffer guarded by channel: " ++ show channelName

-- | Generates the C++ type definition for a launcher field.
-- As described in Note [Expert matmuls], MoE launchers generate
-- expert_matmul_launcher<"name", typename T::launch_matmul, N, K> whereas
-- regular launchers result in T::launch_matmul_for<BufferTypes...>.
launcherField :: (Name ('Tron 'Launcher), LauncherInfo) -> Field
launcherField
  ( launcherName
    , LauncherInfo
        { launcherShape = shape
        , launcherMoe = Just MoeLauncherInfo{moeNumExperts = n, moeTopK = k}
        }
    ) =
    let perExpertTy = expertTensorTypeFromShape (drop 1 shape)
        launchTy = TypenameType $ NamespacedType perExpertTy "launch_matmul"
        emtTy =
          TemplateType
            "expert_matmul_launcher"
            [ ExprType (LiteralExpr (StringLit $ show launcherName))
            , launchTy
            , ExprType (LiteralExpr (IntLit $ fromIntegral n))
            , ExprType (LiteralExpr (IntLit $ fromIntegral k))
            ]
     in Field emtTy (asCpp launcherName)
launcherField
  (launcherName, LauncherInfo{launcherShape = shape, launcherMoe = Nothing}) =
    -- Regular launcher: T::launch_matmul_for<BufferTypes...>
    let baseTy = TemplateType launchMatmulFor $ map batchTensorType shape
        launchMatmulFor = NamespacedType (tensorTypeFromShape shape) "template launch_matmul_for"
     in Field baseTy $ asCpp launcherName

-- | The individual tensor type (btensor_t), used for matmul launcher type
-- parameters. Distinct from bufferType which wraps in indexed_vector.
batchTensorType :: Expr -> Type
batchTensorType width = TemplateType "btensor_t" [ExprType width]

tensorTypeFromShape :: [Expr] -> Type
tensorTypeFromShape shape = TemplateType "dtensor_t" $ map ExprType shape

-- | Like `tensorTypeFromShape` but for per-expert weights (always TP1).
expertTensorTypeFromShape :: [Expr] -> Type
expertTensorTypeFromShape shape = TemplateType "expert_dtensor_t" $ map ExprType shape
