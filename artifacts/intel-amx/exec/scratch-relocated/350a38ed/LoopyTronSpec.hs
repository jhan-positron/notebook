{-# LANGUAGE LambdaCase #-}
{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE PatternSynonyms #-}

module LoopyTronSpec (spec) where

import Control.Exception (SomeException, displayException, evaluate, try)
import Control.Monad (void)
import Data.Char (isSpace)
import Data.List (find, isInfixOf, tails)
import Data.List.NonEmpty qualified as NE
import Data.Map.Ordered qualified as OM
import Data.Map.Strict qualified as M
import Data.Maybe (isJust)
import Data.Set qualified as S
import Data.String (fromString)
import Data.Text qualified as Txt
import Prettyprinter (Pretty (..), defaultLayoutOptions, layoutPretty, pretty)
import Prettyprinter.Render.String (renderString)
import Prettyprinter.Render.Text (renderStrict)
import Test.Syd

import Cpp (Expr (LiteralExpr), Literal (IntLit))
import Cpp qualified
import LoadOp (LoadOp (..), loadOpKey)
import Loopy qualified as L
import Loopy.KernelAccess qualified as KernelAccess
import LoopyCheck qualified
import LoopyTron qualified
import LoopyTron.BufferReuse qualified as BR
import LoopyTron.LivenessAnalysis qualified as LA
import Name
  ( Name
  , NameKind (Cpp, Loopy, Tron)
  , SomeName (..)
  , TronEntity (Buffer, Config, Launcher, Tensor)
  )
import Ops (BinOp (..), ReduceOp (..), TernOp (..), UnOp (..))
import Provenance (ProvenanceSet, SourceID (..), emptyProvenance, singletonProvenance)
import RopeConfig qualified as Rope
import ScalarType (ScalarType (..))
import Semantics
  ( AttentionKvAccess (..)
  , AttentionKvGroupId (..)
  , Semantics (..)
  , WeightSemantics (..)
  )
import Shape (ShapeF (..))
import Size
  ( IterationSpace
  , IterationSpaceF (..)
  , dynamic
  , mul
  , pattern Static
  )
import TargetExecutor qualified as TE
import Tron qualified as T
import TronCheck qualified
import TronCpp qualified
import TronTron qualified
import TypedFx
  ( AttentionType (..)
  , BinaryOp (..)
  , InputTokenRemapping (..)
  , LogitsMunge (..)
  , RopeLayout (..)
  , SoftmaxAttentionGeometry (..)
  )

-- | Render a Tron module to C++ text for substring assertions.
renderCpp :: T.Module -> Txt.Text
renderCpp m =
  renderStrict $
    layoutPretty defaultLayoutOptions $
      pretty $
        TronCpp.process "test_model" TE.Plain m

-- | Render any Pretty value to a String for substring assertions.
render :: Pretty a => a -> String
render = renderString . layoutPretty defaultLayoutOptions . pretty

appearsInOrder :: [Txt.Text] -> Txt.Text -> Bool
appearsInOrder [] _ = True
appearsInOrder (needle : needles) haystack =
  let (_, suffix) = Txt.breakOn needle haystack
   in not (Txt.null suffix)
        && appearsInOrder needles (Txt.drop (Txt.length needle) suffix)

compactCpp :: Txt.Text -> Txt.Text
compactCpp = Txt.filter $ not . isSpace

attentionCallPrefix :: Txt.Text -> Txt.Text -> Int -> Txt.Text
attentionCallPrefix method geometry operationIx =
  Txt.concat
    [ "outer_state.template"
    , method
    , "<"
    , compactCpp geometry
    , ","
    , Txt.pack $ show operationIx
    , ">("
    ]

-- | 'T.example' with a compensated LM-head (wcls) tensor added, so the
-- generated @visit_named_tensors@ exercises the compensated-tensor branch.
-- The frontend aliases a tied head to its input embedding key, so the LoadOp
-- carries a single key.
exampleWithWcls :: T.Module
exampleWithWcls =
  T.example
    { T.modDecls = wclsDecl OM.|< T.modDecls T.example
    }
 where
  wclsDecl =
    ( SomeName ("wcls" :: Name ('Tron 'Tensor))
    , T.TensorInfoE $
        T.TensorInfo
          [LiteralExpr (IntLit 32000), LiteralExpr (IntLit 16)]
          (LoadSafetensors "model.embed_tokens.weight")
          T.Compensated
          T.OrdinaryTensor
          Nothing
          emptyProvenance
    )

loopyWithMissingConfigValue :: L.Module
loopyWithMissingConfigValue =
  L.moeExample
    { L.moduleEnv = map removeHiddenSizeValue $ L.moduleEnv L.moeExample
    }
 where
  removeHiddenSizeValue
    (L.Config var ["hidden_size"] _value prov) =
      L.Config var ["hidden_size"] Nothing prov
  removeHiddenSizeValue stmt = stmt

configInitializationFor
  :: Name ('Tron 'Config)
  -> L.Module
  -> Maybe T.ConfigInitialization
configInitializationFor name loopyModule =
  T.configInitialization
    <$> lookup name (T.getConfigs $ T.modDecls $ LoopyTron.process loopyModule)

someCppName :: Name Cpp -> SomeName
someCppName = SomeName

ix :: L.Variable
ix = L.Variable "ix" (L.LoopIxType QBatchItems) Nothing

denseInput :: L.Variable
denseInput =
  L.Variable "input" (L.Array RealScalar (Just QBatchItems) (Static 8)) Nothing

activation :: L.Variable
activation =
  L.Variable "act" (L.Array RealScalar (Just QBatchItems) (Static 8)) Nothing

denseArray :: String -> L.Variable
denseArray name =
  L.Variable
    (fromString name)
    (L.Array RealScalar (Just QBatchItems) (Static 4))
    Nothing

denseWeight :: String -> L.Variable
denseWeight name =
  L.Variable
    (fromString name)
    (L.Weight (Shape [Static 4, Static 8]))
    Nothing

expertIx :: L.Variable
expertIx =
  L.Variable
    "expert_ix"
    (L.LoopIxType (QBatchItemsExpertPairs "routing" 2))
    Nothing

expertArray :: String -> L.Variable
expertArray = expertArrayFor "routing"

expertArrayFor :: Name Loopy -> String -> L.Variable
expertArrayFor routingName name =
  L.Variable
    (fromString name)
    (L.Array RealScalar (Just (QBatchItemsExpertPairs routingName 2)) (Static 4))
    Nothing

expertWeight :: String -> L.Variable
expertWeight name =
  L.Variable
    (fromString name)
    (L.Weight (Shape [Static 8, Static 4, Static 8]))
    Nothing

indices :: L.Variable
indices =
  L.Variable
    "indices"
    (L.Array IntScalar (Just QBatchItems) (Static 2))
    Nothing

routing :: L.Variable
routing =
  L.Variable "routing" (L.MoeRoutingType 8 2) Nothing

copyKernel :: String -> String -> String -> L.Statement
copyKernel kname src dst =
  L.ParKernel
    kname
    ix
    [ L.Unary
        Copy
        (L.KernelIndexExpr (fromString src) "ix")
        (L.KernelIndexExpr (fromString dst) "ix")
    ]
    emptyProvenance

unaryOpModule :: UnOp -> L.Module
unaryOpModule op =
  L.Module
    [L.Intermediate activation emptyProvenance]
    []
    ( L.Function
        [(denseInput, "input")]
        [ L.ParKernel
            "unary"
            ix
            [ L.Unary
                op
                (L.KernelIndexExpr "input" "ix")
                (L.KernelIndexExpr "act" "ix")
            ]
            emptyProvenance
        ]
        "act"
    )
    []
    Nothing

gapKernel :: Int -> L.Statement
gapKernel n =
  L.ParKernel ("gap_" ++ show n) ix [L.Comment ("gap " ++ show n)] emptyProvenance

writeIndicesKernel :: L.Statement
writeIndicesKernel =
  L.ParKernel
    "write_indices"
    ix
    [ L.Unary
        Copy
        (L.KernelLiteral (Cpp.IntLit 0))
        (L.KernelIndexExpr "indices" "ix")
    ]
    emptyProvenance

expertCopyKernel :: String -> String -> String -> L.Statement
expertCopyKernel = expertCopyKernelFor "routing"

expertCopyKernelFor :: Name Loopy -> String -> String -> String -> L.Statement
expertCopyKernelFor routingName kname src dst =
  L.ParKernel
    kname
    expertIx{L.type_ = L.LoopIxType (QBatchItemsExpertPairs routingName 2)}
    [ L.Unary
        Copy
        (L.KernelIndexExpr (fromString src) "expert_ix")
        (L.KernelIndexExpr (fromString dst) "expert_ix")
    ]
    emptyProvenance

launcherReuseEnv :: [L.EnvStmt]
launcherReuseEnv =
  [ L.Load (denseWeight "w1") (LoadSafetensors "model.w1") False emptyProvenance
  , L.Load (denseWeight "w2") (LoadSafetensors "model.w2") False emptyProvenance
  , L.Intermediate activation emptyProvenance
  , L.Intermediate (denseArray "out1") emptyProvenance
  , L.Intermediate (denseArray "out2") emptyProvenance
  , L.Intermediate (denseArray "sink1") emptyProvenance
  , L.Intermediate (denseArray "output") emptyProvenance
  ]

launcherReuseModule :: Bool -> L.Module
launcherReuseModule allowOutputSlotReuse =
  L.Module
    launcherReuseEnv
    []
    ( L.Function
        [(denseInput, "input")]
        statements
        "output"
    )
    []
    Nothing
 where
  statements
    | allowOutputSlotReuse =
        [ copyKernel "copy_input" "input" "act"
        , L.Matmul "out1" "w1" "act" emptyProvenance
        , copyKernel "consume_out1" "out1" "sink1"
        ]
          ++ map gapKernel [1 .. 5]
          ++ [ L.Matmul "out2" "w2" "act" emptyProvenance
             , copyKernel "consume_out2" "out2" "output"
             ]
    | otherwise =
        [ copyKernel "copy_input" "input" "act"
        , L.Matmul "out1" "w1" "act" emptyProvenance
        , L.Matmul "out2" "w2" "act" emptyProvenance
        , copyKernel "consume_out1" "out1" "sink1"
        , copyKernel "consume_out2" "out2" "output"
        ]

launcherReuseWithoutSlotSharingModule :: L.Module
launcherReuseWithoutSlotSharingModule =
  L.Module
    launcherReuseEnv
    []
    ( L.Function
        [(denseInput, "input")]
        [ copyKernel "copy_input" "input" "act"
        , L.Matmul "out1" "w1" "act" emptyProvenance
        , copyKernel "consume_out1" "out1" "sink1"
        , L.Matmul "out2" "w2" "act" emptyProvenance
        , copyKernel "consume_out2" "out2" "output"
        ]
        "output"
    )
    []
    Nothing

denseMultiUseLauncherModule :: L.Module
denseMultiUseLauncherModule =
  L.Module
    [ L.Load (denseWeight "w1") (LoadSafetensors "model.w1") False emptyProvenance
    , L.Intermediate activation emptyProvenance
    , L.Intermediate (denseArray "out1") emptyProvenance
    , L.Intermediate (denseArray "out2") emptyProvenance
    , L.Intermediate (denseArray "sink1") emptyProvenance
    , L.Intermediate (denseArray "output") emptyProvenance
    ]
    []
    ( L.Function
        [(denseInput, "input")]
        [ copyKernel "copy_input" "input" "act"
        , L.Matmul "out1" "w1" "act" emptyProvenance
        , L.Matmul "out2" "w1" "act" emptyProvenance
        , copyKernel "consume_out1" "out1" "sink1"
        , copyKernel "consume_out2" "out2" "output"
        ]
        "output"
    )
    []
    Nothing

mixedTwoMatrixConsumerModule :: L.Module
mixedTwoMatrixConsumerModule =
  L.Module
    [ L.Load (denseWeight "w1") (LoadSafetensors "model.w1") False emptyProvenance
    , L.Intermediate activation emptyProvenance
    , L.Intermediate (denseArray "out1") emptyProvenance
    , L.Intermediate (denseArray "out2") emptyProvenance
    , L.Intermediate (denseArray "parallel") emptyProvenance
    , L.Intermediate (denseArray "sink1") emptyProvenance
    , L.Intermediate (denseArray "output") emptyProvenance
    ]
    []
    ( L.Function
        [(denseInput, "input")]
        [ copyKernel "copy_input" "input" "act"
        , L.Matmul "out1" "w1" "act" emptyProvenance
        , L.Matmul "out2" "w1" "act" emptyProvenance
        , copyKernel "consume_act" "act" "parallel"
        , copyKernel "consume_out1" "out1" "sink1"
        , copyKernel "consume_out2" "out2" "output"
        ]
        "output"
    )
    []
    Nothing

denseMultiUseDeadOutputLauncherModule :: L.Module
denseMultiUseDeadOutputLauncherModule =
  L.Module
    [ L.Load (denseWeight "w1") (LoadSafetensors "model.w1") False emptyProvenance
    , L.Intermediate activation emptyProvenance
    , L.Intermediate (denseArray "dead") emptyProvenance
    , L.Intermediate (denseArray "output") emptyProvenance
    ]
    []
    ( L.Function
        [(denseInput, "input")]
        [ copyKernel "copy_input" "input" "act"
        , L.Matmul "dead" "w1" "act" emptyProvenance
        , L.Matmul "output" "w1" "act" emptyProvenance
        ]
        "output"
    )
    []
    Nothing

moeLauncherReuseEnv :: LoadOp -> Name Loopy -> [L.EnvStmt]
moeLauncherReuseEnv secondWeightLoadOp secondRouting =
  -- Declare the alias first when the two operations use different routings.
  [ L.Intermediate routing{L.name = secondRouting} emptyProvenance
  | secondRouting /= "routing"
  ]
    ++ [ L.Load
           (expertWeight "expert_good")
           (LoadExpertSafetensors 8 "model.experts.{}.good.weight")
           False
           emptyProvenance
       , L.Load (expertWeight "expert_second") secondWeightLoadOp False emptyProvenance
       , L.Intermediate activation emptyProvenance
       , L.Intermediate indices emptyProvenance
       , L.Intermediate routing emptyProvenance
       , L.Intermediate (expertArray "out1") emptyProvenance
       , L.Intermediate (expertArrayFor secondRouting "out2") emptyProvenance
       , L.Intermediate (expertArray "sink1") emptyProvenance
       , L.Intermediate (expertArrayFor secondRouting "output") emptyProvenance
       ]

moeLauncherReuseModule :: LoadOp -> Name Loopy -> L.Module
moeLauncherReuseModule secondWeightLoadOp secondRouting =
  L.Module
    (moeLauncherReuseEnv secondWeightLoadOp secondRouting)
    []
    ( L.Function
        [(denseInput, "input")]
        ( [ copyKernel "copy_input" "input" "act"
          , writeIndicesKernel
          , L.MoeRoute "routing" "indices" emptyProvenance
          , L.MoeMatmul "out1" "expert_good" "act" "routing" emptyProvenance
          , expertCopyKernel "consume_out1" "out1" "sink1"
          ]
            ++ map gapKernel [1 .. 5]
            ++ [L.MoeRoute secondRouting "indices" emptyProvenance | secondRouting /= "routing"]
            ++ [ L.MoeMatmul "out2" "expert_second" "act" secondRouting emptyProvenance
               , expertCopyKernelFor secondRouting "consume_out2" "out2" "output"
               ]
        )
        "output"
    )
    []
    Nothing

denseLauncherPhases
  :: T.Module
  -> ([Name ('Tron 'Launcher)], [Name ('Tron 'Launcher)], [Name ('Tron 'Launcher)])
denseLauncherPhases mod_ =
  ( [l | T.MatmulFillStmt _ l _ _ _ <- T.mainKernel mod_]
  , [l | T.MatmulPrepareStmt _ l _ <- T.mainKernel mod_]
  , [l | T.MatmulLaunchStmt l _ _ _ <- T.mainKernel mod_]
  )

denseLauncherUses :: T.Module -> [Name ('Tron 'Launcher)]
denseLauncherUses mod_ =
  [l | T.MatmulFillStmt _ l _ _ _ <- T.mainKernel mod_]
    ++ [l | T.MatmulPrepareStmt _ l _ <- T.mainKernel mod_]
    ++ [l | T.MatmulLaunchStmt l _ _ _ <- T.mainKernel mod_]

matmulLaunchers :: T.Module -> [Name ('Tron 'Launcher)]
matmulLaunchers mod_ = [l | T.MatmulLaunchStmt l _ _ _ <- T.mainKernel mod_]

moeMatmulLaunchers :: T.Module -> [Name ('Tron 'Launcher)]
moeMatmulLaunchers mod_ =
  [ T.moeMatmulLauncher operation
  | T.MoeMatmulPrepareAndLaunchStmt operation <- T.mainKernel mod_
  ]

moeMultiUseLauncherModule :: LoadOp -> L.Module
moeMultiUseLauncherModule weightLoadOp =
  L.Module
    [ L.Load
        (expertWeight "expert_good")
        weightLoadOp
        False
        emptyProvenance
    , L.Intermediate activation emptyProvenance
    , L.Intermediate indices emptyProvenance
    , L.Intermediate routing emptyProvenance
    , L.Intermediate (expertArray "out1") emptyProvenance
    , L.Intermediate (expertArray "out2") emptyProvenance
    , L.Intermediate (expertArray "sink1") emptyProvenance
    , L.Intermediate (expertArray "output") emptyProvenance
    ]
    []
    ( L.Function
        [(denseInput, "input")]
        [ copyKernel "copy_input" "input" "act"
        , writeIndicesKernel
        , L.MoeRoute "routing" "indices" emptyProvenance
        , L.MoeMatmul "out1" "expert_good" "act" "routing" emptyProvenance
        , L.MoeMatmul "out2" "expert_good" "act" "routing" emptyProvenance
        , expertCopyKernel "consume_out1" "out1" "sink1"
        , expertCopyKernel "consume_out2" "out2" "output"
        ]
        "output"
    )
    []
    Nothing

assertSeparateLaunchers :: T.Module -> Expectation
assertSeparateLaunchers actual = do
  length (T.getLaunchers (T.modDecls actual)) `shouldBe` 2
  case matmulLaunchers actual of
    [firstLauncher, secondLauncher] ->
      firstLauncher `shouldNotBe` secondLauncher
    other ->
      expectationFailure $ "expected two matmul launches, got " ++ show other

forceLoopyTron :: L.Module -> IO ()
forceLoopyTron mod_ =
  void (evaluate (length (T.mainKernel (LoopyTron.process mod_))))

forceLoopyTronConfigs :: L.Module -> IO ()
forceLoopyTronConfigs mod_ =
  void $
    evaluate
      (length $ T.getConfigs $ T.modDecls $ LoopyTron.process mod_)

shouldPanicContaining :: String -> IO () -> Expectation
shouldPanicContaining needle action = do
  result <- try action :: IO (Either SomeException ())
  case result of
    Left err ->
      show err `shouldSatisfy` isInfixOf needle
    Right () ->
      expectationFailure $ "expected panic containing: " ++ needle

selfProducedEntryReadUsage :: LA.Usage
selfProducedEntryReadUsage =
  LA.Usage $
    M.singleton
      (LA.Time 0)
      (LA.ReadWrite (T.ParP QBatchItems) (T.ParC QBatchItems))

assertRenderFails :: String -> T.Module -> IO ()
assertRenderFails needle tronMod = do
  result <- try (evaluate (Txt.length (renderCpp tronMod)))
  case result of
    Left err ->
      context ("unexpected error: " <> displayException (err :: SomeException)) $
        (Txt.pack needle `Txt.isInfixOf` Txt.pack (displayException err))
          `shouldBe` True
    Right _ -> expectationFailure "TronCpp accepted an invalid module"

orderedKernelAccessModule :: L.Module
orderedKernelAccessModule =
  L.Module
    [ L.Load weight (LoadSafetensors "weight") False emptyProvenance
    , L.Config readOffset ["read_offset"] (Just $ Cpp.IntLit 0) emptyProvenance
    , L.Intermediate x emptyProvenance
    , L.Intermediate selected emptyProvenance
    , L.Intermediate storageOnly emptyProvenance
    , L.Intermediate output emptyProvenance
    , L.Intermediate result emptyProvenance
    ]
    []
    ( L.Function
        []
        [ L.ParKernel
            "prepare_x"
            ixVar
            [ L.LogStmt
                (L.KernelSliceExpr (row "x") (Static 0) 0)
                (Static 0)
                "ix"
                "empty"
                Nothing
            , copyElement 0
            , copyElement 2
            , L.StridedCopy
                (row "x")
                (L.KernelSizeExpr $ Static 0)
                (L.KernelSizeExpr $ Static 2)
                (L.KernelSizeExpr $ Static 2)
                (row "selected")
            , copyElement 1
            , copyElement 3
            , L.Unary
                Copy
                (L.KernelIndexExpr (row "x") $ L.KernelSizeExpr $ dynamic "read_offset")
                (L.KernelSliceExpr (row "selected") (Static 0) 1)
            , L.Unary
                Copy
                (L.KernelSliceExpr (row "x") (dynamic "read_offset") 2)
                (row "selected")
            ]
            emptyProvenance
        , L.ParKernel
            "zero_work"
            ixVar
            [ L.Unary
                Copy
                (L.KernelLiteral $ Cpp.FloatLit 1)
                (L.KernelSliceExpr (row "x") (Static 0) 0)
            , L.StridedCopy
                (row "x")
                (L.KernelSizeExpr $ Static 0)
                (L.KernelSizeExpr $ Static 1)
                (L.KernelSizeExpr $ Static 0)
                (row "storage_only")
            , L.StridedCopy
                (row "storage_only")
                (L.KernelSizeExpr $ Static 0)
                (L.KernelSizeExpr $ Static 1)
                (L.KernelSizeExpr $ Static 0)
                (row "x")
            ]
            emptyProvenance
        , L.Matmul "output" "weight" "x" emptyProvenance
        , copyKernel "return_output" "output" "result"
        ]
        "result"
    )
    []
    Nothing
 where
  array name width =
    L.Variable name (L.Array RealScalar (Just QBatchItems) (Static width)) Nothing
  x = array "x" 4
  selected = array "selected" 2
  storageOnly = array "storage_only" 4
  output = array "output" 4
  result = array "result" 4
  weight = L.Variable "weight" (L.Weight $ Shape [Static 4, Static 4]) Nothing
  readOffset = L.Variable "read_offset" L.IntType Nothing
  ixVar = L.Variable "ix" (L.LoopIxType QBatchItems) Nothing
  row name =
    L.KernelIndexExpr (L.KernelVarExpr name) (L.KernelVarExpr "ix")
  slice name index = L.KernelSliceExpr (row name) (Static index) 1
  copyElement index =
    L.Unary Copy (L.KernelLiteral $ Cpp.FloatLit 1) (slice "x" index)

selfProducedEntryReadModule :: L.Module
selfProducedEntryReadModule =
  selfProducedEntryReadModuleWith $
    L.Variable "j" (L.LoopIxType $ Fin $ dynamic "loop_extent") Nothing

selfProducedEntryReadModuleWith :: L.Variable -> L.Module
selfProducedEntryReadModuleWith loopVar =
  L.Module
    [ L.Config
        loopExtent
        ["loop_extent"]
        (Just $ Cpp.IntLit 1)
        emptyProvenance
    , L.Intermediate x emptyProvenance
    , L.Intermediate output emptyProvenance
    ]
    []
    ( L.Function
        []
        [ L.ParKernel
            "conditionally_prepare_x"
            ix
            [ L.For
                loopVar
                [L.Unary Copy (L.KernelLiteral $ Cpp.FloatLit 1) (row "x")]
            , L.Unary Copy (row "x") (row "output")
            ]
            emptyProvenance
        ]
        "output"
    )
    []
    Nothing
 where
  array name =
    L.Variable name (L.Array RealScalar (Just QBatchItems) $ Static 4) Nothing
  x = array "x"
  output = array "output"
  loopExtent = L.Variable "loop_extent" L.IntType Nothing
  row name =
    L.KernelIndexExpr (L.KernelVarExpr name) (L.KernelVarExpr "ix")

containsStridedCopy :: T.KernelStmt -> Bool
containsStridedCopy T.StridedCopy{} = True
containsStridedCopy (T.For _ _ body) = any containsStridedCopy body
containsStridedCopy _ = False

sliceModule :: L.Module
sliceModule =
  L.Module
    [L.Intermediate outputVar emptyProvenance]
    []
    ( L.Function
        [(inputVar, "input")]
        [L.ParKernel "copy_head_slices" ixVar [L.For hVar [copyStmt]] emptyProvenance]
        "output"
    )
    []
    Nothing
 where
  inputVar = L.Variable "input" (L.Array L.RealScalar (Just QBatchItems) (Static 2048)) Nothing
  outputVar =
    L.Variable
      "output"
      (L.Array L.RealScalar (Just QBatchItems) (Static 2048))
      Nothing
  ixVar = L.Variable "ix" (L.LoopIxType QBatchItems) Nothing
  hVar = L.Variable "h" (L.LoopIxType (Fin (Static 8))) Nothing
  ix = dynamic "ix"
  h = dynamic "h"
  headOffset = h `mul` Static 256
  inputSlice =
    L.KernelSliceExpr
      (L.KernelIndexExpr (L.KernelVarExpr "input") (L.KernelSizeExpr ix))
      headOffset
      256
  outputSlice =
    L.KernelSliceExpr
      (L.KernelIndexExpr (L.KernelVarExpr "output") (L.KernelSizeExpr ix))
      headOffset
      256
  copyStmt = L.Unary Copy inputSlice outputSlice

weightedRmsNormSliceModule :: L.Module
weightedRmsNormSliceModule = weightedRmsNormSliceModuleFor RmsNorm

shiftedRmsNormSliceModule :: L.Module
shiftedRmsNormSliceModule = weightedRmsNormSliceModuleFor ShiftedRmsNorm

weightedRmsNormSliceModuleFor :: TernOp -> L.Module
weightedRmsNormSliceModuleFor rmsNormOp =
  L.Module
    [ L.Load rmsWeight (LoadSafetensors "rms_w") False emptyProvenance
    , L.Intermediate outputVar emptyProvenance
    ]
    []
    ( L.Function
        [(inputVar, "input")]
        [L.ParKernel "rmsnorm_head_slices" ixVar [L.For hVar [normStmt]] emptyProvenance]
        "output"
    )
    []
    Nothing
 where
  rmsWeight = L.Variable "rms_w" (L.Weight (Shape [Static 256])) Nothing
  inputVar = L.Variable "input" (L.Array L.RealScalar (Just QBatchItems) (Static 2048)) Nothing
  outputVar =
    L.Variable
      "output"
      (L.Array L.RealScalar (Just QBatchItems) (Static 2048))
      Nothing
  ixVar = L.Variable "ix" (L.LoopIxType QBatchItems) Nothing
  hVar = L.Variable "h" (L.LoopIxType (Fin (Static 8))) Nothing
  ix = dynamic "ix"
  h = dynamic "h"
  headOffset = h `mul` Static 256
  headSlice name =
    L.KernelSliceExpr
      (L.KernelIndexExpr (L.KernelVarExpr name) (L.KernelSizeExpr ix))
      headOffset
      256
  normStmt =
    L.Ternary
      rmsNormOp
      (L.KernelVarExpr "rms_w")
      (headSlice "input")
      (L.KernelLiteral $ Cpp.FloatLit 1.0e-6)
      (headSlice "output")

residualRmsNormModule :: Integer -> L.Module
residualRmsNormModule width =
  residualRmsNormModuleWithRows RmsNorm width width id

shiftedResidualRmsNormModule :: Integer -> L.Module
shiftedResidualRmsNormModule width =
  residualRmsNormModuleWithRows ShiftedRmsNorm width width id

residualRmsNormSliceModule :: Integer -> L.Module
residualRmsNormSliceModule width =
  residualRmsNormModuleWithRows RmsNorm width 512 $ \row ->
    L.KernelSliceExpr row (Static 0) width

residualRmsNormModuleWithRows
  :: TernOp
  -> Integer
  -> Integer
  -> (L.KernelExpr -> L.KernelExpr)
  -> L.Module
residualRmsNormModuleWithRows rmsNormOp width backingWidth selectRow =
  L.Module
    [ L.Load rmsWeight (LoadSafetensors "rms_w") False emptyProvenance
    , L.Intermediate residualVar emptyProvenance
    , L.Intermediate outputVar emptyProvenance
    ]
    []
    ( L.Function
        [(inputVar, "input"), (otherVar, "other")]
        [L.ParKernel "residual_rmsnorm" ixVar [addStmt, normStmt] emptyProvenance]
        "output"
    )
    []
    Nothing
 where
  rowType = L.Array L.RealScalar (Just QBatchItems) (Static backingWidth)
  rmsWeight = L.Variable "rms_w" (L.Weight (Shape [Static width])) Nothing
  inputVar = L.Variable "input" rowType Nothing
  otherVar = L.Variable "other" rowType Nothing
  residualVar = L.Variable "residual" rowType Nothing
  outputVar = L.Variable "output" rowType Nothing
  ixVar = L.Variable "ix" (L.LoopIxType QBatchItems) Nothing
  row name =
    selectRow $
      L.KernelIndexExpr (L.KernelVarExpr name) (L.KernelVarExpr "ix")
  addStmt = L.Binary Add (row "input") (row "other") (row "residual")
  normStmt =
    L.Ternary
      rmsNormOp
      (L.KernelVarExpr "rms_w")
      (row "residual")
      (L.KernelLiteral $ Cpp.FloatLit 1.0e-6)
      (row "output")

scalarResidualRmsNormModule :: Float -> L.Module
scalarResidualRmsNormModule weight =
  residualRmsNormWeightModule
    []
    (L.KernelLiteral $ Cpp.FloatLit weight)

zeroRankTensorRmsNormModule :: L.Module
zeroRankTensorRmsNormModule =
  residualRmsNormWeightModule
    [ L.Load
        (L.Variable "rms_weight" (L.Weight (Shape [])) Nothing)
        (LoadSafetensors "rms_weight")
        False
        emptyProvenance
    ]
    (L.KernelVarExpr "rms_weight")

bufferWeightRmsNormModule :: Bool -> L.Module
bufferWeightRmsNormModule sliced =
  L.Module
    [ L.Load lookupWeight (LoadSafetensors "rms_lut") False emptyProvenance
    , L.Intermediate sourceVar emptyProvenance
    , L.Intermediate residualVar emptyProvenance
    , L.Intermediate outputVar emptyProvenance
    ]
    []
    ( L.Function
        [(tokenVar, "token_job_tokens")]
        [ L.ParKernel
            "buffer_weight_rmsnorm"
            ixVar
            [lookupStmt, addStmt, normStmt]
            emptyProvenance
        ]
        "output"
    )
    []
    Nothing
 where
  vectorType = L.Array RealScalar (Just QBatchItems) (Static 256)
  sourceType =
    L.Array RealScalar (Just QBatchItems) (Static backingWidth)
  lookupWeight =
    L.Variable
      "rms_lut"
      (L.Weight (Shape [Static 32000, Static backingWidth]))
      Nothing
  sourceVar = L.Variable "rms_weight" sourceType Nothing
  residualVar = L.Variable "residual" vectorType Nothing
  outputVar = L.Variable "output" vectorType Nothing
  tokenVar =
    L.Variable "tokens" (L.Array IntScalar (Just QBatchItems) (Static 1)) Nothing
  ixVar = L.Variable "ix" (L.LoopIxType QBatchItems) Nothing
  row name =
    L.KernelIndexExpr (L.KernelVarExpr name) (L.KernelVarExpr "ix")
  token =
    L.KernelIndexExpr (row "tokens") (L.KernelSizeExpr (Static 0))
  source
    | sliced = L.KernelSliceExpr (row "rms_weight") (Static 0) 256
    | otherwise = row "rms_weight"
  backingWidth
    | sliced = 512
    | otherwise = 256
  lookupStmt =
    L.Binary Index (L.KernelVarExpr "rms_lut") token (row "rms_weight")
  addStmt = L.Binary Add source source (row "residual")
  normStmt =
    L.Ternary
      RmsNorm
      source
      (row "residual")
      (L.KernelLiteral $ Cpp.FloatLit 1.0e-6)
      (row "output")

bufferScalarRmsNormModule :: L.Module
bufferScalarRmsNormModule =
  bufferScalarRmsNormModuleFor RmsNorm

shiftedBufferScalarRmsNormModule :: L.Module
shiftedBufferScalarRmsNormModule =
  bufferScalarRmsNormModuleFor ShiftedRmsNorm

bufferScalarRmsNormModuleFor :: TernOp -> L.Module
bufferScalarRmsNormModuleFor rmsNormOp =
  L.Module
    [ L.Load lookupWeight (LoadSafetensors "rms_lut") False emptyProvenance
    , L.Intermediate inputVar emptyProvenance
    , L.Intermediate scalarVar emptyProvenance
    , L.Intermediate residualVar emptyProvenance
    , L.Intermediate outputVar emptyProvenance
    ]
    []
    ( L.Function
        [(tokenVar, "token_job_tokens")]
        [ L.ParKernel
            "buffer_scalar_rmsnorm"
            ixVar
            [lookupStmt, reduceStmt, addStmt, normStmt]
            emptyProvenance
        ]
        "output"
    )
    []
    Nothing
 where
  vectorType = L.Array RealScalar (Just QBatchItems) (Static 256)
  scalarType = L.Array RealScalar (Just QBatchItems) (Static 1)
  lookupWeight =
    L.Variable "rms_lut" (L.Weight (Shape [Static 32000, Static 256])) Nothing
  scalarVar = L.Variable "rms_scalars" scalarType Nothing
  inputVar = L.Variable "input" vectorType Nothing
  residualVar = L.Variable "residual" vectorType Nothing
  outputVar = L.Variable "output" vectorType Nothing
  tokenVar =
    L.Variable "tokens" (L.Array IntScalar (Just QBatchItems) (Static 1)) Nothing
  ixVar = L.Variable "ix" (L.LoopIxType QBatchItems) Nothing
  row name =
    L.KernelIndexExpr (L.KernelVarExpr name) (L.KernelVarExpr "ix")
  token =
    L.KernelIndexExpr (row "tokens") (L.KernelSizeExpr (Static 0))
  scalar =
    L.KernelIndexExpr
      (row "rms_scalars")
      (L.KernelLiteral $ Cpp.IntLit 0)
  lookupStmt =
    L.Binary Index (L.KernelVarExpr "rms_lut") token (row "input")
  reduceStmt = L.Reduce ReduceSum (row "input") (row "rms_scalars")
  addStmt = L.Binary Add (row "input") (row "input") (row "residual")
  normStmt =
    L.Ternary
      rmsNormOp
      scalar
      (row "residual")
      (L.KernelLiteral $ Cpp.FloatLit 1.0e-6)
      (row "output")

residualRmsNormWeightModule :: [L.EnvStmt] -> L.KernelExpr -> L.Module
residualRmsNormWeightModule weightEnv weight =
  L.Module
    ( weightEnv
        ++ [ L.Intermediate residualVar emptyProvenance
           , L.Intermediate outputVar emptyProvenance
           ]
    )
    []
    ( L.Function
        [(inputVar, "input"), (otherVar, "other")]
        [L.ParKernel "scalar_residual_rmsnorm" ixVar [addStmt, normStmt] emptyProvenance]
        "output"
    )
    []
    Nothing
 where
  vectorType = L.Array L.RealScalar (Just QBatchItems) (Static 256)
  inputVar = L.Variable "input" vectorType Nothing
  otherVar = L.Variable "other" vectorType Nothing
  residualVar = L.Variable "residual" vectorType Nothing
  outputVar = L.Variable "output" vectorType Nothing
  ixVar = L.Variable "ix" (L.LoopIxType QBatchItems) Nothing
  vector name = L.KernelIndexExpr (L.KernelVarExpr name) (L.KernelVarExpr "ix")
  addStmt = L.Binary Add (vector "input") (vector "other") (vector "residual")
  normStmt =
    L.Ternary
      RmsNorm
      weight
      (vector "residual")
      (L.KernelLiteral $ Cpp.FloatLit 1.0e-6)
      (vector "output")

unitRmsNormSliceModule :: L.Module
unitRmsNormSliceModule =
  L.Module
    [L.Intermediate outputVar emptyProvenance]
    []
    ( L.Function
        [(inputVar, "input")]
        [ L.ParKernel
            "norm_head_slices"
            ixVar
            [L.For hVar [normStmt]]
            emptyProvenance
        ]
        "output"
    )
    []
    Nothing
 where
  inputVar =
    L.Variable
      "input"
      (L.Array L.RealScalar (Just QBatchItems) (Static 2048))
      Nothing
  outputVar =
    L.Variable
      "output"
      (L.Array L.RealScalar (Just QBatchItems) (Static 2048))
      Nothing
  ixVar = L.Variable "ix" (L.LoopIxType QBatchItems) Nothing
  hVar = L.Variable "h" (L.LoopIxType (Fin (Static 8))) Nothing
  ix = dynamic "ix"
  h = dynamic "h"
  headOffset = h `mul` Static 256
  headSlice name =
    L.KernelSliceExpr
      ( L.KernelIndexExpr
          (L.KernelVarExpr name)
          (L.KernelSizeExpr ix)
      )
      headOffset
      256
  normStmt =
    L.Ternary
      RmsNorm
      (L.KernelLiteral (Cpp.FloatLit 1.0))
      (headSlice "input")
      (L.KernelLiteral (Cpp.FloatLit 1.0e-6))
      (headSlice "output")

tokenPositionsModule :: L.Module
tokenPositionsModule =
  L.Module
    [L.Intermediate outputVar emptyProvenance]
    []
    ( L.Function
        [(positionsVar, "token_job_positions")]
        [L.ParKernel "copy_token_positions" ixVar [copyStmt] emptyProvenance]
        "output"
    )
    []
    Nothing
 where
  positionsVar = L.Variable "positions" (L.Array L.IntScalar (Just QBatchItems) (Static 1)) Nothing
  outputVar =
    L.Variable
      "output"
      (L.Array L.IntScalar (Just QBatchItems) (Static 1))
      Nothing
  ixVar = L.Variable "ix" (L.LoopIxType QBatchItems) Nothing
  ix = dynamic "ix"
  inputExpr =
    L.KernelIndexExpr
      (L.KernelVarExpr "positions")
      (L.KernelSizeExpr ix)
  outputExpr =
    L.KernelIndexExpr
      (L.KernelVarExpr "output")
      (L.KernelSizeExpr ix)
  copyStmt = L.Unary Copy inputExpr outputExpr

ropeConfigModule
  :: Maybe Double
  -> [(Rope.RopeParameters, Integer, Integer)]
  -> L.Module
ropeConfigModule maybeTheta configs =
  tokenPositionsModule
    { L.moduleEnv =
        thetaEnv
          <> zipWith ropeEnv [0 :: Int ..] configs
          <> L.moduleEnv tokenPositionsModule
    }
 where
  thetaEnv = case maybeTheta of
    Nothing -> []
    Just theta ->
      [ L.Config
          (L.Variable "rope_theta" L.FloatType Nothing)
          ["rope_theta"]
          (Just $ Cpp.DoubleLit theta)
          emptyProvenance
      ]
  ropeEnv index (parameters, representedRotaryDim, activeRotaryDim) =
    L.RopeCfg
      ( L.Variable
          (fromString $ "rope_config_" <> show index)
          L.RopeCfgType
          Nothing
      )
      RopeLayoutChunked
      parameters
      representedRotaryDim
      activeRotaryDim
      emptyProvenance

moeRouterNumberingModule :: Integer -> L.Module
moeRouterNumberingModule attentionLayer =
  L.Module
    [ L.Intermediate (denseArray "q") emptyProvenance
    , L.Intermediate (denseArray "k") emptyProvenance
    , L.Intermediate (denseArray "v") emptyProvenance
    , L.Intermediate (denseArray "attention_out") emptyProvenance
    , L.Intermediate (routeIndices "indices_0" 2) emptyProvenance
    , L.Intermediate (routeIndices "indices_1" 3) emptyProvenance
    , L.Intermediate (route "routing_0" 2) emptyProvenance
    , L.Intermediate (route "routing_1" 3) emptyProvenance
    , L.Intermediate (denseArray "output") emptyProvenance
    ]
    []
    ( L.Function
        [(denseArray "input", "input")]
        [ copyKernel "copy_q" "input" "q"
        , copyKernel "copy_k" "input" "k"
        , copyKernel "copy_v" "input" "v"
        , writeRouteIndicesKernel "indices_0"
        , L.MoeRoute "routing_0" "indices_0" emptyProvenance
        , L.Attention
            "attention_out"
            "q"
            (WritePrivateKv "k" "v")
            attentionLayer
            Nothing
            FullCausal
            Nothing
            0.5
            emptyProvenance
        , writeRouteIndicesKernel "indices_1"
        , L.MoeRoute "routing_1" "indices_1" emptyProvenance
        , copyKernel "copy_output" "attention_out" "output"
        ]
        "output"
    )
    []
    Nothing
 where
  routeIndices name topK =
    L.Variable
      (fromString name)
      (L.Array IntScalar (Just QBatchItems) (Static topK))
      Nothing
  route name topK =
    L.Variable
      (fromString name)
      (L.MoeRoutingType 8 topK)
      Nothing
  writeRouteIndicesKernel name =
    L.ParKernel
      ("write_" ++ name)
      ix
      [ L.Unary
          Copy
          (L.KernelLiteral (Cpp.IntLit 0))
          (L.KernelIndexExpr (fromString name) "ix")
      ]
      emptyProvenance

moePlacementModule :: L.Module
moePlacementModule =
  L.moeExample
    { L.moduleEnv =
        reorderExpertLoads
          (map rewriteCheckpointLayer (L.moduleEnv L.moeExample))
          ++ [ L.Load
                 ( L.Variable
                     "expert_bias"
                     (L.Weight (Shape [Static 8, Static 512]))
                     Nothing
                 )
                 (LoadExpertSafetensors 8 "model.layers.11.mlp.experts.{}.bias")
                 False
                 emptyProvenance
             , L.Intermediate
                 ( L.Variable
                     "bias_view"
                     (L.ExpertViewType "routing" 8 2 (Static 512))
                     Nothing
                 )
                 emptyProvenance
             ]
          ++ [ L.Load
                 ( L.Variable
                     (fromString name)
                     (L.Weight (Shape [Static 512, Static 512]))
                     (Just (Weight role, 11))
                 )
                 (LoadSafetensors (name ++ ".weight"))
                 False
                 emptyProvenance
             | (name, role) <-
                 [("key_matrix", WeightK), ("value_matrix", WeightV), ("query_matrix", WeightQ)]
             ]
    , L.moduleFunction =
        baseFunction
          { L.functionStmts =
              concatMap addExpertBias (L.functionStmts baseFunction)
          }
    }
 where
  baseFunction = L.moduleFunction L.moeExample

  reorderExpertLoads
    ( w1@(L.Load (L.Variable "expert_w1" _ _) _ _ _)
        : w2@(L.Load (L.Variable "expert_w2" _ _) _ _ _)
        : rest
      ) = w2 : w1 : rest
  reorderExpertLoads (decl : rest) = decl : reorderExpertLoads rest
  reorderExpertLoads [] = []

  rewriteCheckpointLayer (L.Load var loadOp compensated prov) =
    L.Load (markRouter loadOp var) (rewriteLoadOp loadOp) compensated prov
  rewriteCheckpointLayer stmt = stmt

  markRouter (LoadSafetensors "model.gate.weight") var =
    var{L.semantics = Just (Weight WeightRouter, 11)}
  markRouter _ var = var

  rewriteLoadOp (LoadSafetensors "model.gate.weight") =
    LoadSafetensors "model.layers.11.mlp.gate.weight"
  rewriteLoadOp (LoadExpertSafetensors 8 "model.experts.{}.w1.weight") =
    LoadExpertSafetensors 8 "model.layers.11.mlp.experts.{}.w1.weight"
  rewriteLoadOp (LoadExpertSafetensors 8 "model.experts.{}.w2.weight") =
    LoadExpertSafetensors 8 "model.layers.11.mlp.experts.{}.w2.weight"
  rewriteLoadOp loadOp = loadOp

  addExpertBias (L.MoeBlend output routingName scales input Nothing prov) =
    [ L.MoeExpertView "bias_view" routingName "expert_bias" prov
    , L.MoeBlend output routingName scales input (Just "bias_view") prov
    ]
  addExpertBias stmt = [stmt]

moeRouterIds :: T.Module -> [Integer]
moeRouterIds mod_ =
  [ T.unMoeRouterId routerId
  | T.MoeRouteStmt _ _ routerId _ <- T.mainKernel mod_
  ]
windowedModule :: T.Module
windowedModule = LoopyTron.process explicitAttentionModule

attentionProv :: ProvenanceSet
attentionProv = singletonProvenance $ SourceID "attention-operation-test"

attentionArray :: String -> Integer -> L.Variable
attentionArray name width =
  L.Variable
    (fromString name)
    (L.Array RealScalar (Just QBatchItems) (Static width))
    Nothing

attentionCopy :: String -> String -> String -> L.Statement
attentionCopy kernelName input output =
  L.ParKernel
    kernelName
    ix
    [ L.Unary
        Copy
        (L.KernelIndexExpr (fromString input) "ix")
        (L.KernelIndexExpr (fromString output) "ix")
    ]
    emptyProvenance

explicitAttentionModule :: L.Module
explicitAttentionModule =
  L.Module
    { L.moduleEnv =
        [ L.Load
            (L.Variable "sinks" (L.Weight (Shape [Static 2])) Nothing)
            (LoadSafetensors "model.layers.7.self_attn.sinks.weight")
            False
            emptyProvenance
        , L.Intermediate (attentionArray "q" 8) emptyProvenance
        , L.Intermediate (attentionArray "k" 4) emptyProvenance
        , L.Intermediate (attentionArray "v" 4) emptyProvenance
        , L.Intermediate (attentionArray "attn_out" 8) emptyProvenance
        , L.Intermediate (attentionArray "output" 8) emptyProvenance
        ]
    , L.moduleLiteralCpps = []
    , L.moduleFunction =
        L.Function
          [ (attentionArray "q_input" 8, "q_input")
          , (attentionArray "k_input" 4, "k_input")
          , (attentionArray "v_input" 4, "v_input")
          ]
          [ attentionCopy "copy_q" "q_input" "q"
          , attentionCopy "copy_k" "k_input" "k"
          , attentionCopy "copy_v" "v_input" "v"
          , L.Attention
              "attn_out"
              "q"
              (WritePrivateKv "k" "v")
              7
              Nothing
              (SlidingWindow 128)
              (Just "sinks")
              0.125
              attentionProv
          , attentionCopy "copy_output" "attn_out" "output"
          ]
          "output"
    , L.moduleInputTokenRemappings = []
    , L.moduleLogitsMunge = Nothing
    }

sameBufferKvAttentionModule :: AttentionKvAccess (Name Loopy) -> L.Module
sameBufferKvAttentionModule kvAccess =
  L.Module
    { L.moduleEnv =
        [ L.Intermediate (attentionArray "q" 8) emptyProvenance
        , L.Intermediate (attentionArray "kv" 4) emptyProvenance
        , L.Intermediate (attentionArray "attn_out" 8) emptyProvenance
        , L.Intermediate (attentionArray "output" 8) emptyProvenance
        ]
    , L.moduleLiteralCpps = []
    , L.moduleFunction =
        L.Function
          [ (attentionArray "q_input" 8, "q_input")
          , (attentionArray "kv_input" 4, "kv_input")
          ]
          [ attentionCopy "copy_q" "q_input" "q"
          , attentionCopy "copy_kv" "kv_input" "kv"
          , L.Attention
              "attn_out"
              "q"
              kvAccess
              7
              (Just $ SoftmaxAttentionGeometry 2 1 4)
              FullCausal
              Nothing
              0.5
              attentionProv
          , attentionCopy "copy_output" "attn_out" "output"
          ]
          "output"
    , L.moduleInputTokenRemappings = []
    , L.moduleLogitsMunge = Nothing
    }

uniformExplicitAttentionModule :: L.Module
uniformExplicitAttentionModule =
  explicitAttentionModule
    { L.moduleEnv = attentionConfigs ++ L.moduleEnv explicitAttentionModule
    , L.moduleFunction =
        (L.moduleFunction explicitAttentionModule)
          { L.functionStmts =
              map attachGeometry $
                L.functionStmts $
                  L.moduleFunction explicitAttentionModule
          }
    }
 where
  geometry = SoftmaxAttentionGeometry 2 1 4
  attentionConfigs =
    [ intConfig "num_attention_heads" 2
    , intConfig "num_key_value_heads" 1
    , intConfig "head_dim" 4
    ]
  intConfig name value =
    L.Config
      (L.Variable (fromString name) L.IntType Nothing)
      [name]
      (Just $ Cpp.IntLit value)
      emptyProvenance
  attachGeometry (L.Attention out q kvAccess layer _ _ sinks scale prov) =
    L.Attention out q kvAccess layer (Just geometry) FullCausal sinks scale prov
  attachGeometry statement = statement

queryOnlyGeometryModule :: L.Module
queryOnlyGeometryModule =
  L.Module
    { L.moduleEnv =
        attentionConfigs
          ++ [ L.Intermediate (attentionArray name width) emptyProvenance
             | (suffix, qWidth, _, _) <- operations
             , (name, width) <-
                 [ ("q" ++ suffix, qWidth)
                 , ("k" ++ suffix, 64)
                 , ("v" ++ suffix, 64)
                 , ("attn" ++ suffix, qWidth)
                 ]
             ]
          ++ [ L.Intermediate (attentionArray "discard0" 512) emptyProvenance
             , L.Intermediate (attentionArray "output" 1024) emptyProvenance
             ]
    , L.moduleLiteralCpps = []
    , L.moduleFunction =
        L.Function
          ( concat
              [ [
                  ( attentionArray ("q" ++ suffix ++ "_input") qWidth
                  , "q" ++ suffix ++ "_input"
                  )
                ,
                  ( attentionArray ("k" ++ suffix ++ "_input") 64
                  , "k" ++ suffix ++ "_input"
                  )
                ,
                  ( attentionArray ("v" ++ suffix ++ "_input") 64
                  , "v" ++ suffix ++ "_input"
                  )
                ]
              | (suffix, qWidth, _, _) <- operations
              ]
          )
          ( concatMap attentionStatements operations
              ++ [ attentionCopy "consume_attn0" "attn0" "discard0"
                 , attentionCopy "copy_output" "attn1" "output"
                 ]
          )
          "output"
    , L.moduleInputTokenRemappings = []
    , L.moduleLogitsMunge = Nothing
    }
 where
  standardGeometry = SoftmaxAttentionGeometry 8 1 64
  operations =
    [ ("0", 512, 2, standardGeometry)
    , ("1", 1024, 9, SoftmaxAttentionGeometry 16 1 64)
    ]
  attentionConfigs =
    [ intConfig "num_attention_heads" 8
    , intConfig "num_key_value_heads" 1
    , intConfig "head_dim" 64
    ]
  intConfig name value =
    L.Config
      (L.Variable (fromString name) L.IntType Nothing)
      [name]
      (Just $ Cpp.IntLit value)
      emptyProvenance
  attentionStatements (suffix, _, layer, geometry) =
    [ attentionCopy ("copy_q" ++ suffix) ("q" ++ suffix ++ "_input") ("q" ++ suffix)
    , attentionCopy ("copy_k" ++ suffix) ("k" ++ suffix ++ "_input") ("k" ++ suffix)
    , attentionCopy ("copy_v" ++ suffix) ("v" ++ suffix ++ "_input") ("v" ++ suffix)
    , L.Attention
        (fromString $ "attn" ++ suffix)
        (fromString $ "q" ++ suffix)
        ( WritePrivateKv
            (fromString $ "k" ++ suffix)
            (fromString $ "v" ++ suffix)
        )
        layer
        (Just geometry)
        FullCausal
        Nothing
        0.125
        attentionProv
    ]

sparseAttentionModule :: L.Module
sparseAttentionModule =
  L.Module
    { L.moduleEnv =
        [ L.Intermediate (attentionArray name width) emptyProvenance
        | (name, width) <-
            [ ("q", 8)
            , ("k", 4)
            , ("v", 4)
            , ("attn_mid", 8)
            , ("q2", 8)
            , ("k2", 4)
            , ("v2", 4)
            , ("attn_out", 8)
            , ("output", 8)
            ]
        ]
    , L.moduleLiteralCpps = []
    , L.moduleFunction =
        L.Function
          [ (attentionArray "q_input" 8, "q_input")
          , (attentionArray "k_input" 4, "k_input")
          , (attentionArray "v_input" 4, "v_input")
          , (attentionArray "k2_input" 4, "k2_input")
          , (attentionArray "v2_input" 4, "v2_input")
          ]
          [ attentionCopy "copy_q" "q_input" "q"
          , attentionCopy "copy_k" "k_input" "k"
          , attentionCopy "copy_v" "v_input" "v"
          , L.Attention
              "attn_mid"
              "q"
              (WritePrivateKv "k" "v")
              2
              Nothing
              FullCausal
              Nothing
              0.5
              attentionProv
          , attentionCopy "copy_mid" "attn_mid" "q2"
          , attentionCopy "copy_k2" "k2_input" "k2"
          , attentionCopy "copy_v2" "v2_input" "v2"
          , L.Attention
              "attn_out"
              "q2"
              (WritePrivateKv "k2" "v2")
              9
              Nothing
              (SlidingWindow 64)
              Nothing
              0.5
              attentionProv
          , attentionCopy "copy_output" "attn_out" "output"
          ]
          "output"
    , L.moduleInputTokenRemappings = []
    , L.moduleLogitsMunge = Nothing
    }

sinkedSparseAttentionModule :: [Integer] -> L.Module
sinkedSparseAttentionModule sinkLayers =
  sparseAttentionModule
    { L.moduleEnv = sinkLoad : L.moduleEnv sparseAttentionModule
    , L.moduleFunction =
        (L.moduleFunction sparseAttentionModule)
          { L.functionStmts =
              map addSink $ L.functionStmts $ L.moduleFunction sparseAttentionModule
          }
    }
 where
  sinkLoad =
    L.Load
      (L.Variable "shared_sinks" (L.Weight (Shape [Static 2])) Nothing)
      (LoadSafetensors "shared.attn.sinks.weight")
      False
      emptyProvenance
  addSink
    (L.Attention output q kvAccess layer geometry attnType _ scale provenance)
      | layer `elem` sinkLayers =
          L.Attention
            output
            q
            kvAccess
            layer
            geometry
            attnType
            (Just "shared_sinks")
            scale
            provenance
  addSink statement = statement

distinctSinkSparseAttentionModule :: L.Module
distinctSinkSparseAttentionModule =
  base
    { L.moduleEnv = secondSinkLoad : L.moduleEnv base
    , L.moduleFunction =
        (L.moduleFunction base)
          { L.functionStmts =
              map replaceSecondSink $ L.functionStmts $ L.moduleFunction base
          }
    }
 where
  base = sinkedSparseAttentionModule [2, 9]
  secondSinkLoad =
    L.Load
      (L.Variable "second_sinks" (L.Weight (Shape [Static 2])) Nothing)
      (LoadSafetensors "second.attn.sinks.weight")
      False
      emptyProvenance
  replaceSecondSink
    (L.Attention output q kvAccess 9 geometry attnType _ scale provenance) =
      L.Attention
        output
        q
        kvAccess
        9
        geometry
        attnType
        (Just "second_sinks")
        scale
        provenance
  replaceSecondSink statement = statement
sharedAttentionModule :: L.Module
sharedAttentionModule =
  sparseAttentionModule
    { L.moduleEnv = filter keepEnv $ L.moduleEnv sparseAttentionModule
    , L.moduleFunction =
        sparseFunction
          { L.functionParams = filter keepParam $ L.functionParams sparseFunction
          , L.functionStmts = map shareKv $ filter keepStmt $ L.functionStmts sparseFunction
          }
    }
 where
  sparseFunction = L.moduleFunction sparseAttentionModule
  readerKvNames = ["k2", "v2"]
  readerKvInputs = ["k2_input", "v2_input"]
  group = AttentionKvGroupId 0
  sharedGeometry = Just $ SoftmaxAttentionGeometry 2 1 4

  keepEnv (L.Intermediate var _) = L.name var `notElem` readerKvNames
  keepEnv _ = True
  keepParam (var, _) = L.name var `notElem` readerKvInputs
  keepStmt (L.ParKernel name _ _ _) = name `notElem` ["copy_k2", "copy_v2"]
  keepStmt _ = True

  shareKv (L.Attention out q (WritePrivateKv k v) layer _ typ sinks scale prov)
    | layer == 2 =
        L.Attention out q (WriteSharedKv group k v) layer sharedGeometry typ sinks scale prov
    | layer == 9 =
        L.Attention out q (ReadSharedKv group) layer sharedGeometry typ sinks scale prov
  shareKv stmt = stmt

mapSharedAttentionStatements
  :: ([L.Statement] -> [L.Statement])
  -> L.Module
  -> L.Module
mapSharedAttentionStatements transform mod_ =
  mod_
    { L.moduleFunction =
        function
          { L.functionStmts = replace transformed $ L.functionStmts function
          }
    }
 where
  function = L.moduleFunction mod_
  transformed = transform [stmt | stmt@L.Attention{} <- L.functionStmts function]
  replace (replacement : replacements) (L.Attention{} : statements) =
    replacement : replace replacements statements
  replace [] (L.Attention{} : _) =
    error "mapSharedAttentionStatements: too few replacements"
  replace replacements (stmt : statements) = stmt : replace replacements statements
  replace [] [] = []
  replace _ [] = error "mapSharedAttentionStatements: too many replacements"

duplicateReader :: [L.Statement] -> [L.Statement]
duplicateReader = map $ \case
  L.Attention out q (ReadSharedKv group) layer geometry typ sinks scale prov ->
    L.Attention
      out
      q
      (WriteSharedKv group "k" "v")
      layer
      geometry
      typ
      sinks
      scale
      prov
  stmt -> stmt

changeReaderGeometry :: [L.Statement] -> [L.Statement]
changeReaderGeometry = map $ \case
  L.Attention out q access@(ReadSharedKv _) layer _ typ sinks scale prov ->
    L.Attention
      out
      q
      access
      layer
      (Just $ SoftmaxAttentionGeometry 2 2 4)
      typ
      sinks
      scale
      prov
  stmt -> stmt

denseSharedSlotModule :: L.Module
denseSharedSlotModule =
  L.Module
    { L.moduleEnv =
        [ L.Intermediate (attentionArray name width) emptyProvenance
        | (name, width) <-
            [ ("q0", 8)
            , ("k0", 4)
            , ("v0", 4)
            , ("attn0", 8)
            , ("attn1", 8)
            , ("attn2", 8)
            , ("k3", 4)
            , ("v3", 4)
            , ("attn3", 8)
            , ("output", 8)
            ]
        ]
    , L.moduleLiteralCpps = []
    , L.moduleFunction =
        L.Function
          [ (attentionArray "q0_input" 8, "q0_input")
          , (attentionArray "k0_input" 4, "k0_input")
          , (attentionArray "v0_input" 4, "v0_input")
          , (attentionArray "k3_input" 4, "k3_input")
          , (attentionArray "v3_input" 4, "v3_input")
          ]
          [ attentionCopy "copy_q0" "q0_input" "q0"
          , attentionCopy "copy_k0" "k0_input" "k0"
          , attentionCopy "copy_v0" "v0_input" "v0"
          , attention "attn0" "q0" (WriteSharedKv group "k0" "v0") 2
          , attention "attn1" "attn0" (ReadSharedKv group) 3
          , attention "attn2" "attn1" (ReadSharedKv group) 4
          , attentionCopy "copy_k3" "k3_input" "k3"
          , attentionCopy "copy_v3" "v3_input" "v3"
          , attention "attn3" "attn2" (WritePrivateKv "k3" "v3") 5
          , attentionCopy "copy_output" "attn3" "output"
          ]
          "output"
    , L.moduleInputTokenRemappings = []
    , L.moduleLogitsMunge = Nothing
    }
 where
  group = AttentionKvGroupId 0
  geometry = Just $ SoftmaxAttentionGeometry 2 1 4
  attention output query access layer =
    L.Attention
      output
      query
      access
      layer
      geometry
      FullCausal
      Nothing
      0.5
      attentionProv

heterogeneousAttentionModule :: L.Module
heterogeneousAttentionModule =
  L.Module
    { L.moduleEnv =
        [ L.Intermediate (attentionArray name width) emptyProvenance
        | (suffix, qWidth, kvWidth, _, _) <- operations
        , (name, width) <-
            [ ("q" ++ suffix, qWidth)
            , ("k" ++ suffix, kvWidth)
            , ("v" ++ suffix, kvWidth)
            , ("attn" ++ suffix, qWidth)
            , ("sink" ++ suffix, qWidth)
            ]
        , name /= "sink2"
        ]
          ++ [L.Intermediate (attentionArray "output" 4096) emptyProvenance]
    , L.moduleLiteralCpps = []
    , L.moduleFunction =
        L.Function
          ( concat
              [ [ (attentionArray ("q" ++ suffix ++ "_input") qWidth, "q" ++ suffix ++ "_input")
                , (attentionArray ("k" ++ suffix ++ "_input") kvWidth, "k" ++ suffix ++ "_input")
                , (attentionArray ("v" ++ suffix ++ "_input") kvWidth, "v" ++ suffix ++ "_input")
                ]
              | (suffix, qWidth, kvWidth, _, _) <- operations
              ]
          )
          ( concatMap attentionStatements operations
              ++ [attentionCopy "copy_output" "attn2" "output"]
          )
          "output"
    , L.moduleInputTokenRemappings = []
    , L.moduleLogitsMunge = Nothing
    }
 where
  operations =
    [ ("0", 512, 64, 2, SoftmaxAttentionGeometry 8 1 64)
    , ("1", 1536, 256, 9, SoftmaxAttentionGeometry 12 2 128)
    , ("2", 4096, 1024, 11, SoftmaxAttentionGeometry 16 4 256)
    ]
  attentionStatements (suffix, _, _, layer, geometry) =
    [ attentionCopy ("copy_q" ++ suffix) ("q" ++ suffix ++ "_input") ("q" ++ suffix)
    , attentionCopy ("copy_k" ++ suffix) ("k" ++ suffix ++ "_input") ("k" ++ suffix)
    , attentionCopy ("copy_v" ++ suffix) ("v" ++ suffix ++ "_input") ("v" ++ suffix)
    , L.Attention
        (fromString $ "attn" ++ suffix)
        (fromString $ "q" ++ suffix)
        ( WritePrivateKv
            (fromString $ "k" ++ suffix)
            (fromString $ "v" ++ suffix)
        )
        layer
        (Just geometry)
        FullCausal
        Nothing
        (1 / sqrt (fromIntegral $ softmaxHeadSize geometry))
        attentionProv
    ]
      ++ [ attentionCopy
             ("consume_attn" ++ suffix)
             ("attn" ++ suffix)
             ("sink" ++ suffix)
         | suffix /= "2"
         ]

sameKvAttentionModule :: L.Module
sameKvAttentionModule =
  L.Module
    { L.moduleEnv =
        [ L.Config
            (L.Variable name L.IntType Nothing)
            [path]
            (Just $ IntLit value)
            emptyProvenance
        | (name, path, value) <-
            [ ("cfg_layers", "num_hidden_layers", 10)
            , ("cfg_q_heads", "num_attention_heads", 8)
            , ("cfg_kv_heads", "num_key_value_heads", 1)
            , ("cfg_head_size", "head_dim", 64)
            ]
        ]
          ++ [ L.Intermediate (attentionArray name width) emptyProvenance
             | (name, width) <-
                 [ ("same_q0", 512)
                 , ("same_k0", 64)
                 , ("same_v0", 64)
                 , ("same_attn0", 512)
                 , ("same_sink0", 512)
                 , ("same_q1", 1024)
                 , ("same_k1", 64)
                 , ("same_v1", 64)
                 , ("same_attn1", 1024)
                 , ("same_output", 1024)
                 ]
             ]
    , L.moduleLiteralCpps = []
    , L.moduleFunction =
        L.Function
          [ (attentionArray "same_q0_input" 512, "same_q0_input")
          , (attentionArray "same_k0_input" 64, "same_k0_input")
          , (attentionArray "same_v0_input" 64, "same_v0_input")
          , (attentionArray "same_q1_input" 1024, "same_q1_input")
          , (attentionArray "same_k1_input" 64, "same_k1_input")
          , (attentionArray "same_v1_input" 64, "same_v1_input")
          ]
          [ attentionCopy "same_copy_q0" "same_q0_input" "same_q0"
          , attentionCopy "same_copy_k0" "same_k0_input" "same_k0"
          , attentionCopy "same_copy_v0" "same_v0_input" "same_v0"
          , L.Attention
              "same_attn0"
              "same_q0"
              (WritePrivateKv "same_k0" "same_v0")
              2
              (Just $ SoftmaxAttentionGeometry 8 1 64)
              FullCausal
              Nothing
              0.125
              attentionProv
          , attentionCopy "same_consume0" "same_attn0" "same_sink0"
          , attentionCopy "same_copy_q1" "same_q1_input" "same_q1"
          , attentionCopy "same_copy_k1" "same_k1_input" "same_k1"
          , attentionCopy "same_copy_v1" "same_v1_input" "same_v1"
          , L.Attention
              "same_attn1"
              "same_q1"
              (WritePrivateKv "same_k1" "same_v1")
              9
              (Just $ SoftmaxAttentionGeometry 16 1 64)
              FullCausal
              Nothing
              0.125
              attentionProv
          , attentionCopy "same_copy_output" "same_attn1" "same_output"
          ]
          "same_output"
    , L.moduleInputTokenRemappings = []
    , L.moduleLogitsMunge = Nothing
    }

legacyAttentionModule :: L.Module
legacyAttentionModule =
  explicitAttentionModule
    { L.moduleFunction =
        (L.moduleFunction explicitAttentionModule)
          { L.functionStmts =
              map legacyAttention $
                L.functionStmts $
                  L.moduleFunction explicitAttentionModule
          }
    }
 where
  legacyAttention (L.Attention output q kvAccess layer _ attnType sinks scale prov) =
    L.Attention output q kvAccess layer Nothing attnType sinks scale prov
  legacyAttention stmt = stmt

makeReadOnly :: T.Statement -> T.Statement
makeReadOnly (T.AttentionStmt attention) =
  T.AttentionStmt $
    attention
      { T.attentionKvSlot = T.KvSlotId 3
      , T.attentionKvWrite = Nothing
      }
makeReadOnly stmt = stmt

makeSecondWriterShare :: T.Statement -> T.Statement
makeSecondWriterShare (T.AttentionStmt attention)
  | T.attentionOpId attention == T.AttentionOpId 1 =
      T.AttentionStmt attention{T.attentionKvSlot = T.KvSlotId 2}
makeSecondWriterShare stmt = stmt

selectSoftwareAttention :: T.Statement -> T.Statement
selectSoftwareAttention (T.AttentionStmt attention) =
  T.AttentionStmt
    attention{T.attentionHardwareCapability = T.SoftwareAttentionOnly}
selectSoftwareAttention statement = statement

makeSecondUseFirstLayerAndDistinctSlot :: T.Statement -> T.Statement
makeSecondUseFirstLayerAndDistinctSlot (T.PrepareAttentionStmt preparation)
  | T.prepareAttentionOpId preparation == T.AttentionOpId 1 =
      T.PrepareAttentionStmt $
        preparation{T.prepareAttentionModelLayer = T.ModelLayerId 2}
makeSecondUseFirstLayerAndDistinctSlot (T.AttentionStmt attention)
  | T.attentionOpId attention == T.AttentionOpId 1 =
      T.AttentionStmt $
        attention
          { T.attentionModelLayer = T.ModelLayerId 2
          , T.attentionKvSlot = T.KvSlotId 3
          }
makeSecondUseFirstLayerAndDistinctSlot stmt = stmt

makeNonuniform :: T.Statement -> T.Statement
makeNonuniform (T.AttentionStmt attention) =
  T.AttentionStmt attention{T.attentionKvSlot = T.KvSlotId 3}
makeNonuniform stmt = stmt

isAttentionPrepare :: T.Statement -> Bool
isAttentionPrepare (T.PrepareAttentionStmt _) = True
isAttentionPrepare _ = False

mixedConsumerFor
  :: (Ord a, Show a) => Int -> IterationSpaceF k a -> T.Consumer (IterationSpaceF k a)
mixedConsumerFor matrixCount iterSpace =
  case T.normalizeConsumers [T.MatrixC matrixCount, T.ParC iterSpace] of
    Right consumer -> consumer
    Left err -> error err

parallelSingleHostConsumerFor
  :: (Ord a, Show a) => IterationSpaceF k a -> T.Consumer (IterationSpaceF k a)
parallelSingleHostConsumerFor iterSpace =
  case T.normalizeConsumers [T.ParC iterSpace, T.SingleHostC] of
    Right consumer -> consumer
    Left err -> error err

-- | The MoE example with a host-parallel read of the top-k indices after
-- routing, so routing and the parallel kernel both read the indices channel.
mixedMoeIndicesModule :: L.Module
mixedMoeIndicesModule =
  L.moeExample
    { L.moduleEnv = indicesTable : scratch : L.moduleEnv L.moeExample
    , L.moduleFunction = function{L.functionStmts = statements}
    }
 where
  function = L.moduleFunction L.moeExample
  statements = concatMap insertParallelRead $ L.functionStmts function
  insertParallelRead statement@L.MoeRoute{} = [statement, readIndices]
  insertParallelRead statement = [statement]
  scratch =
    L.Intermediate
      ( L.Variable
          "indices_as_real"
          (L.Array RealScalar (Just QBatchItems) (Static 2))
          Nothing
      )
      emptyProvenance
  indicesTable =
    L.Load
      (L.Variable "indices_table" (L.Weight $ Shape [Static 8, Static 1]) Nothing)
      (LoadSafetensors "indices_table")
      False
      emptyProvenance
  loopVar = L.Variable "indices_read_ix" (L.LoopIxType QBatchItems) Nothing
  row name =
    L.KernelIndexExpr
      (L.KernelVarExpr name)
      (L.KernelVarExpr $ L.name loopVar)
  readIndices =
    L.ParKernel
      "read_indices"
      loopVar
      [ L.Binary
          Index
          (L.KernelVarExpr "indices_table")
          (row "indices")
          (row "indices_as_real")
      ]
      emptyProvenance

checkMixedMoeReadersShareChannel :: IO ()
checkMixedMoeReadersShareChannel = do
  let tronMod = LoopyTron.process mixedMoeIndicesModule
      cpp = renderCpp tronMod
      indicesInfo = T.readDecl "indices_channel" $ T.modDecls tronMod
  T.channelConsumer indicesInfo
    `shouldBe` parallelSingleHostConsumerFor QBatchItems
  TronCheck.checkChannelSync (T.modDecls tronMod) (T.mainKernel tronMod)
    `shouldBe` Right ()
  ("tensor_latch<signaled_producer_t>> indices_channel;" `Txt.isInfixOf` cpp)
    `shouldBe` True
  ("indices_channel.reset(n_workers, n_workers);" `Txt.isInfixOf` cpp)
    `shouldBe` True
  ("q_batch->indices_channel.start_reading_at(task_ix);" `Txt.isInfixOf` cpp)
    `shouldBe` True

mixedConsumersShareBuffer
  :: T.Consumer (IterationSpace Loopy)
  -> T.Consumer (IterationSpace Loopy)
  -> Either String Bool
mixedConsumersShareBuffer firstConsumer secondConsumer = do
  (assignment, _, _, _, _) <-
    BR.computeBufferAssignment BR.MidpointPrepares env [] liveness "result"
  let buffers = BR.unBufferAssignment assignment
  case (M.lookup "first" buffers, M.lookup "second" buffers) of
    (Just first, Just second) -> Right $ first == second
    _ -> Left "missing mixed-consumer buffer assignment"
 where
  buffer name =
    L.Intermediate
      (L.Variable name (L.Array RealScalar (Just QBatchItems) (Static 8)) Nothing)
      emptyProvenance
  env = [buffer "first", buffer "second"]
  usage writeTime readTime consumer =
    LA.Usage $
      M.fromList
        [ (writeTime, LA.Write $ T.ParP QBatchItems)
        , (readTime, LA.Read consumer)
        ]
  liveness =
    LA.LivenessAnalysis $
      M.fromList
        [ ("first", usage (LA.Time 0) (LA.Time 1) firstConsumer)
        , ("second", usage (LA.Time 8) (LA.Time 9) secondConsumer)
        ]

-- | 'L.laneDomainExample' with device routers, which run the gate as an
-- 'L.Matmul' on the FPGA. Each host router kernel becomes three statements: a
-- kernel with the statements before its 'MatVec', the gate 'L.Matmul', and a
-- kernel with the top-k after it.
laneDomainWithDeviceRouters :: L.Module
laneDomainWithDeviceRouters =
  L.laneDomainExample
    { L.moduleFunction =
        function{L.functionStmts = concatMap split (L.functionStmts function)}
    }
 where
  function = L.moduleFunction L.laneDomainExample
  split (L.ParKernel name var body prov)
    | (norm, L.Binary MatVec (L.KernelVarExpr gate) input output : topK) <-
        break isMatVec body
    , L.KernelIndexExpr (L.KernelVarExpr inputName) _ <- input
    , L.KernelIndexExpr (L.KernelVarExpr outputName) _ <- output =
        [ L.ParKernel (name ++ "_norm") var norm prov
        , L.Matmul outputName gate inputName prov
        , L.ParKernel (name ++ "_topk") var topK prov
        ]
  split stmt = [stmt]
  isMatVec = \case
    L.Binary MatVec _ _ _ -> True
    _ -> False

-- | Pairs each channel prepare in the main kernel with the statement it
-- precedes. That statement is the next one that neither prepares a channel nor
-- starts a channel read or write. It is "end" if no such statement follows.
prepareSites :: T.Module -> [(String, String)]
prepareSites tron =
  [ (render channel, maybe "end" site (find (not . opensAccess) rest))
  | T.ChannelPrepareStmt channel _ : rest <- tails (T.mainKernel tron)
  ]
 where
  opensAccess = \case
    T.ChannelPrepareStmt{} -> True
    T.ChannelStartWritingStmt{} -> True
    T.ChannelStartReadingStmt{} -> True
    _ -> False
  site = \case
    T.HostStmt kernel _ -> render kernel
    T.MatmulFillStmt tensor _ _ _ _ -> "matmul " ++ render tensor
    T.PrepareAttentionStmt preparation ->
      "attention " ++ show (T.unModelLayerId $ T.prepareAttentionModelLayer preparation)
    T.MoeRouteStmt _ _ router _ -> "moe_route " ++ show (T.unMoeRouterId router)
    T.MoeMatmulPrepareAndLaunchStmt operation ->
      "moe_matmul " ++ render (T.moeMatmulTensor operation)
    stmt -> render stmt

-- | The prepare schedule that buffer reuse computes for a module under a
-- placement. The liveness uses an empty aligned lane domain, which is the
-- domain LoopyTron finds in a module without host routers.
prepareScheduleWith
  :: BR.PreparePlacement -> L.Module -> Either String BR.PrepareSchedule
prepareScheduleWith placement mod_ = do
  liveness <- LA.lifetimeAnalysis (const False) mod_
  (_, _, _, prepares, _) <-
    BR.computeBufferAssignment
      placement
      (L.moduleEnv mod_)
      (L.functionStmts function)
      liveness
      (L.functionReturn function)
  pure prepares
 where
  function = L.moduleFunction mod_

-- | The prepare times of each binder in a 40-statement function with one MoE
-- router window, (10, 14]: the times after the 'L.MoeRoute' at 10, up to and
-- including the 'L.MoeMatmul' at 14. The MoeRoute writes @routing@, and the
-- MoeMatmul is its last read. Every other statement is an empty filler kernel.
-- Each entry is a buffer or routing binder with the times of its write and its
-- last read.
routerWindowPrepares
  :: BR.PreparePlacement
  -> [(Name Loopy, L.Type, (Int, Int))]
  -> Either String (M.Map (Name Loopy) [LA.Time])
routerWindowPrepares placement entries = do
  (_, _, _, prepares, _) <-
    BR.computeBufferAssignment placement env (map stmtAt [0 .. 39]) liveness "result"
  pure $
    M.fromListWith
      (flip (++))
      [(name, [time]) | (time, names) <- M.toList prepares, name <- names]
 where
  binders = (L.name routing, L.type_ routing, (10, 14)) : entries
  env =
    L.Load
      (expertWeight "expert_w")
      (LoadExpertSafetensors 8 "experts.{}.w")
      False
      emptyProvenance
      : [ L.Intermediate (L.Variable name ty Nothing) emptyProvenance
        | (name, ty, _) <- binders
        ]
  stmtAt :: Int -> L.Statement
  stmtAt 10 = L.MoeRoute (L.name routing) "indices" emptyProvenance
  stmtAt 14 =
    L.MoeMatmul "expert_out" "expert_w" "expert_in" (L.name routing) emptyProvenance
  stmtAt _ = L.ParKernel "filler" ix [] emptyProvenance
  liveness =
    LA.LivenessAnalysis $
      M.fromList [(name, usage ty lifetime) | (name, ty, lifetime) <- binders]
  usage ty (write, lastRead) =
    LA.Usage $
      M.fromList
        [ (LA.Time write, LA.Write producer)
        , (LA.Time lastRead, LA.Read consumer)
        ]
   where
    (producer, consumer) = case ty of
      L.MoeRoutingType{} -> (T.MoeRoutingP, T.MoeRoutingC)
      _ -> (T.ParP QBatchItems, T.MatrixC 1)

spec :: Spec
spec =
  describe "LoopyTron" $ do
    it "resolves numeric loop bounds in their enclosing scope" $ do
      let config = L.Variable "extent" L.IntType Nothing
          -- The local index must not shadow the generated model receiver.
          outer = L.Variable "model" (L.LoopIxType $ Fin $ dynamic "extent") Nothing
          inner = L.Variable "j" (L.LoopIxType $ Fin $ dynamic "model") Nothing
          write = L.Unary Copy (L.KernelLiteral $ Cpp.FloatLit 1) (L.KernelIndexExpr "output" "ix")
          kernel = L.ParKernel "numeric_bounds" ix [write, L.For outer [L.For inner []]] emptyProvenance
          loopy =
            L.Module
              [ L.Config config ["head_dim"] (Just $ Cpp.IntLit 4) emptyProvenance
              , L.Intermediate (denseArray "output") emptyProvenance
              ]
              []
              (L.Function [] [kernel] "output")
              []
              Nothing
      LoopyCheck.check LoopyCheck.EscapesForbidden loopy `shouldBe` []
      let cpp = compactCpp $ renderCpp $ LoopyTron.process loopy
      cpp
        `shouldSatisfy` Txt.isInfixOf "for(size_tmodel=0;model<this->model.head_size;model+=1)"
      cpp `shouldSatisfy` Txt.isInfixOf "for(size_tj=0;j<model;j+=1)"
    it "copies a framework input row through its scalar storage" $ do
      let cpp = compactCpp $ renderCpp $ LoopyTron.process tokenPositionsModule
      cpp
        `shouldSatisfy` Txt.isInfixOf
          "tron::strided_copy(tron::const_view<uint32_t,false,false,tron::seq<1>>(&(outer_state.token_job_positions[ix])),0,1,1,output[ix]);"
    it "reads a framework input element through its row view" $ do
      let cpp = compactCpp $ renderCpp $ LoopyTron.process bufferScalarRmsNormModule
      cpp
        `shouldSatisfy` Txt.isInfixOf
          "model.rms_lut[tron::const_view<uint32_t,false,false,tron::seq<1>>(&(outer_state.token_job_tokens[ix]))[0]]"
    describe "C++ control condition rendering" $ do
      let lhs = Cpp.Var "lhs"
          rhs = Cpp.Var "rhs"
          equality = Cpp.BinOp Cpp.Eq lhs rhs
          emptyBlock = Cpp.Block []
          compact = filter $ not . isSpace
      it "uses one set of parentheses for if conditions" $ do
        compact (render $ Cpp.IfStmt equality emptyBlock Nothing)
          `shouldBe` "if(lhs==rhs){}"
      it "uses one set of parentheses for constexpr conditions" $ do
        compact (render $ Cpp.IfConstexprStmt equality emptyBlock Nothing)
          `shouldBe` "ifconstexpr(lhs==rhs){}"
      it "uses no extra parentheses around for conditions" $ do
        let loop =
              Cpp.ForStmt
                (Cpp.Declare "size_t" "i" $ Just $ LiteralExpr $ IntLit 0)
                (Cpp.BinOp Cpp.Eq (Cpp.Var "i") (Cpp.Var "limit"))
                (Cpp.IncAssignment (Cpp.Var "i") Cpp.Add $ LiteralExpr $ IntLit 1)
                emptyBlock
        compact (render loop) `shouldBe` "for(size_ti=0;i==limit;i+=1){}"
      it "preserves nested grouping and non-binary conditions" $ do
        let nested = Cpp.BinOp Cpp.Eq (Cpp.BinOp Cpp.Add lhs rhs) (Cpp.Var "sum")
        compact (render $ Cpp.IfStmt nested emptyBlock Nothing)
          `shouldBe` "if((lhs+rhs)==sum){}"
        compact (render $ Cpp.IfStmt (Cpp.Var "ready") emptyBlock Nothing)
          `shouldBe` "if(ready){}"
    it "keeps reads satisfied by earlier kernel writes local" $ do
      LoopyCheck.check LoopyCheck.EscapesForbidden orderedKernelAccessModule
        `shouldBe` []
      let tron@(T.Module decls _ _ _ _ _ _) =
            LoopyTron.process orderedKernelAccessModule
          cpp = renderCpp tron
          matrixChannels =
            [ (inputChannel, outputChannel)
            | T.MatmulLaunchStmt _ outputChannel (inputChannel, _) _ <- T.mainKernel tron
            ]
          stridedKernels =
            [ info
            | (_, info) <- T.getKernels decls
            , any containsStridedCopy $ T.kernelBody info
            ]
      (inputChannel, outputChannel) <- case matrixChannels of
        [channels] -> pure channels
        other -> expectationFailure $ "expected one matrix channel pair, got " ++ show other
      inputChannelInfo <- case lookup inputChannel $ T.getChannels decls of
        Just info -> pure info
        Nothing -> expectationFailure $ "missing matrix input channel " ++ show inputChannel
      (kernel, zeroWorkKernel) <- case stridedKernels of
        [first, second]
          | null (T.kernelWriteBuffers first) -> pure (second, first)
          | null (T.kernelWriteBuffers second) -> pure (first, second)
        other ->
          expectationFailure $
            "expected one productive and one zero-work strided kernel, got "
              ++ show other
      T.channelProducer inputChannelInfo `shouldBe` T.ParP QBatchItems
      T.channelConsumer inputChannelInfo `shouldBe` T.MatrixC 1
      T.kernelEntryReadBuffers kernel `shouldBe` []
      S.fromList (T.kernelWriteBuffers kernel)
        `shouldBe` S.fromList ["selected", "x"]
      T.kernelEntryReadBuffers zeroWorkKernel `shouldBe` []
      T.kernelWriteBuffers zeroWorkKernel `shouldBe` []
      map fst (T.getBuffers decls) `shouldContain` ["storage_only"]
      let channel = Txt.pack $ show inputChannel
      context "does not make the producer wait on its own channel" $
        (Txt.concat ["q_batch->", channel, ".start_reading_at"] `Txt.isInfixOf` cpp)
          `shouldBe` False
      context "retains the matrix consumer synchronization" $ do
        appearsInOrder
          [ "kernel_prepare_x(q_batch, 0, n_workers);"
          , Txt.concat ["q_batch->", channel, ".start_reading(0);"]
          ]
          cpp
          `shouldBe` True
        (Txt.concat ["q_batch->", channel, ".finish_reading(0)"] `Txt.isInfixOf` cpp)
          `shouldBe` True
      context "waits for the matrix result before the return kernel reads it" $
        Txt.count
          (Txt.concat ["q_batch->", Txt.pack $ show outputChannel, ".start_reading_at"])
          cpp
          `shouldBe` 2
      context "does not publish a write from the zero-work kernel" $
        Txt.count (Txt.concat ["q_batch->", channel, ".finish_writing_at"]) cpp
          `shouldBe` 1
    it "rejects a self-produced entry read" $ do
      let fallbackModule =
            selfProducedEntryReadModuleWith $
              L.Variable "j" (L.LoopIxType $ Fin $ Static 1000000000) Nothing
      mapM_
        ( \(label, loopy) -> context label $ do
            LoopyCheck.check LoopyCheck.EscapesForbidden loopy `shouldBe` []
            LA.LivenessAnalysis usages <-
              either expectationFailure pure $ LA.lifetimeAnalysis (const False) loopy
            M.lookup "x" usages
              `shouldBe` Just
                ( LA.Usage $
                    M.singleton
                      (LA.Time 0)
                      (LA.ReadWrite (T.ParP QBatchItems) (T.ParC QBatchItems))
                )
            shouldPanicContaining "cannot be satisfied by its own write" $
              forceLoopyTron loopy
        )
        [ ("unknown loop", selfProducedEntryReadModule)
        , ("whole-kernel conservative fallback", fallbackModule)
        ]
    it "keeps a Nary result assignment and its following read local" $ do
      let row name = L.KernelIndexExpr (L.KernelVarExpr name) "ix"
          loopy =
            L.Module
              [ L.Intermediate (denseArray "x") emptyProvenance
              , L.Intermediate (denseArray "output") emptyProvenance
              ]
              []
              ( L.Function
                  []
                  [ L.ParKernel
                      "assign_nary"
                      ix
                      [ L.Nary "sqrtf" [L.KernelLiteral $ Cpp.FloatLit 4] (row "x")
                      , L.Unary Copy (row "x") (row "output")
                      ]
                      emptyProvenance
                  ]
                  "output"
              )
              []
              Nothing
      LoopyCheck.check LoopyCheck.EscapesAllowed loopy `shouldBe` []
      LA.LivenessAnalysis usages <-
        either expectationFailure pure $ LA.lifetimeAnalysis (const False) loopy
      M.lookup "x" usages
        `shouldBe` Just (LA.Usage $ M.singleton (LA.Time 0) $ LA.LocalReadWrite $ T.ParP QBatchItems)
      let tron = LoopyTron.process loopy
      case T.getKernels $ T.modDecls tron of
        [(_, kernel)] -> T.kernelEntryReadBuffers kernel `shouldBe` []
        other -> expectationFailure $ "expected one Nary assignment kernel, got " ++ show other
      ("sqrtf(" `Txt.isInfixOf` renderCpp tron) `shouldBe` True
    it "specializes TopK only when its fixed-size preconditions are proven" $ do
      let row name = L.KernelIndexExpr (L.KernelVarExpr name) "ix"
          array scalar name width =
            L.Variable name (L.Array scalar (Just QBatchItems) width) Nothing
          fixture width sliceWidth count =
            L.Module
              [ L.Config
                  (L.Variable "input_width" L.IntType Nothing)
                  ["input_width"]
                  (Just $ Cpp.IntLit 4)
                  emptyProvenance
              , L.Intermediate (array RealScalar "input" width) emptyProvenance
              , L.Intermediate (array IntScalar "indices" $ Static 8) emptyProvenance
              , L.Intermediate (array RealScalar "values" $ Static 8) emptyProvenance
              , L.Intermediate (array RealScalar "output" $ Static 8) emptyProvenance
              ]
              []
              ( L.Function
                  []
                  [ L.ParKernel
                      "topk"
                      ix
                      [ L.Unary Copy (L.KernelLiteral $ Cpp.FloatLit 2) (row "input")
                      , L.TopK
                          ( case sliceWidth of
                              Nothing -> row "input"
                              Just n -> L.KernelSliceExpr (row "input") (Static 1) n
                          )
                          (L.KernelLiteral $ Cpp.IntLit count)
                          (L.KernelLiteral $ Cpp.BoolLit True)
                          (L.KernelLiteral $ Cpp.BoolLit True)
                          (row "indices")
                          (row "values")
                      , L.Unary Copy (L.KernelLiteral $ Cpp.FloatLit 0) (row "output")
                      ]
                      emptyProvenance
                  ]
                  "output"
              )
              []
              Nothing
          cases =
            [ (Static 4, Nothing, 0, False)
            , (Static 4, Nothing, 2, True)
            , (Static 4, Nothing, 4, True)
            , (Static 4, Nothing, 6, False)
            , (dynamic "input_width", Nothing, 2, False)
            , (Static 4, Just 2, 2, True)
            , (Static 4, Just 2, 3, False)
            ]
      mapM_
        ( \(width, sliceWidth, count, specialized) ->
            context (show (width, sliceWidth, count)) $ do
              let loopy = fixture width sliceWidth count
              LoopyCheck.check LoopyCheck.EscapesForbidden loopy `shouldBe` []
              let cpp = renderCpp $ LoopyTron.process loopy
                  fixed = "tron::topk_fixed<" <> Txt.pack (show count) <> ">"
              Txt.count fixed cpp `shouldBe` if specialized then 1 else 0
              Txt.count "tron::topk(" cpp `shouldBe` if specialized then 0 else 1
        )
        cases
    it "starts channel reads at the first external consumer" $ do
      let usage =
            LA.Usage $
              M.fromList
                [ (LA.Time 0, LA.LocalReadWrite $ T.ParP QBatchItems)
                , (LA.Time 3, LA.Read T.SingleHostC)
                , (LA.Time 5, LA.Read T.SingleHostC)
                ]
      LA.lifetimeBounds usage
        `shouldBe` Right
          (LA.LiveBounds $ LA.LifetimeBounds (LA.Time 0) (LA.Time 0) (LA.Time 3) (LA.Time 5))
      let lateLocalRead =
            LA.Usage $
              M.fromList
                [ (LA.Time 0, LA.Write $ T.ParP QBatchItems)
                , (LA.Time 3, LA.Read T.SingleHostC)
                , (LA.Time 5, LA.LocalReadWrite $ T.ParP QBatchItems)
                ]
      LA.lifetimeBounds lateLocalRead
        `shouldBe` Right
          (LA.LiveBounds $ LA.LifetimeBounds (LA.Time 0) (LA.Time 5) (LA.Time 3) (LA.Time 5))
    it "retains storage for producer-local reads without channel consumers" $ do
      let usage = LA.Usage $ M.singleton (LA.Time 2) $ LA.LocalReadWrite $ T.ParP QBatchItems
      LA.lifetimeBounds usage
        `shouldBe` Right
          (LA.LiveBounds $ LA.LifetimeBounds (LA.Time 2) (LA.Time 2) (LA.Time 2) (LA.Time 2))
      LA.channelRequirement LA.NormalVar usage `shouldBe` Right LA.NoChannel
    it "preserves ordinary external read bounds" $ do
      let usage =
            LA.Usage $
              M.fromList
                [ (LA.Time 0, LA.Write $ T.ParP QBatchItems)
                , (LA.Time 2, LA.Read T.SingleHostC)
                ]
      LA.lifetimeBounds usage
        `shouldBe` Right
          (LA.LiveBounds $ LA.LifetimeBounds (LA.Time 0) (LA.Time 0) (LA.Time 2) (LA.Time 2))
    it "finishes fused top-k production before its single-host routing read" $ do
      let source = L.moeExample
          func = L.moduleFunction source
          copyIndices (L.ParKernel "copy" binder _ prov) =
            L.ParKernel
              "copy"
              binder
              [ L.Unary
                  Copy
                  (L.KernelLiteral $ Cpp.FloatLit 1)
                  (L.KernelIndexExpr "ins" "ix")
              ]
              prov
          copyIndices (L.ParKernel "topk_softmax" binder body prov) =
            L.ParKernel
              "topk_softmax"
              binder
              ( body
                  ++ [ L.Binary
                         Index
                         "indices_table"
                         ( L.KernelIndexExpr
                             (L.KernelIndexExpr "indices" "ix")
                             (L.KernelSizeExpr $ Static 0)
                         )
                         (L.KernelIndexExpr "indices_as_real" "ix")
                     ]
              )
              prov
          copyIndices stmt = stmt
          loopy =
            source
              { L.moduleEnv =
                  L.Load
                    ( L.Variable
                        "indices_table"
                        (L.Weight $ Shape [Static 8, Static 1])
                        Nothing
                    )
                    (LoadSafetensors "indices_table")
                    False
                    emptyProvenance
                    : L.Intermediate
                      ( L.Variable
                          "indices_as_real"
                          (L.Array RealScalar (Just QBatchItems) (Static 1))
                          Nothing
                      )
                      emptyProvenance
                    : L.moduleEnv source
              , L.moduleFunction =
                  func
                    { L.functionParams = []
                    , L.functionStmts = map copyIndices $ L.functionStmts func
                    }
              }
          tron = LoopyTron.process loopy
          cpp = renderCpp tron
      LoopyCheck.check LoopyCheck.EscapesForbidden loopy `shouldBe` []
      TronCheck.checkChannelSync (T.modDecls tron) (T.mainKernel tron)
        `shouldBe` Right ()
      ("tensor_latch<signaled_producer_t>> indices_channel;" `Txt.isInfixOf` cpp)
        `shouldBe` True
      Txt.count "q_batch->indices_channel.start_reading(0);" cpp `shouldBe` 1
      appearsInOrder
        [ "q_batch->indices_channel.start_writing(0);"
        , "kernel_topk_softmax("
        , "q_batch->indices_channel.finish_writing(0);"
        , "q_batch->indices_channel.start_reading(0);"
        , "build_moe_routing_from_indices<8, 2>(indices"
        , "q_batch->indices_channel.finish_reading(0);"
        ]
        cpp
        `shouldBe` True
    it "reports the kernel name when access analysis fails" $ do
      let output = denseArray "bad_output"
          badLoop =
            L.For
              (L.Variable "j" (L.LoopIxType $ Fin $ Static (-1)) Nothing)
              []
          loopy =
            L.Module
              [L.Intermediate output emptyProvenance]
              []
              ( L.Function
                  []
                  [L.ParKernel "bad_access" ix [badLoop] emptyProvenance]
                  "bad_output"
              )
              []
              Nothing
      LA.lifetimeAnalysis (const False) loopy
        `shouldBe` Left
          ( "Kernel access analysis failed for \"bad_access\" at Time 0: "
              <> "negative static kernel-loop extent: -1"
          )
      shouldPanicContaining "\"bad_access\" at Time 0" $ forceLoopyTron loopy
    it "scopes the outer kernel binder over a module array" $ do
      let shadowedArray = denseArray "ix"
          output = denseArray "shadow_output"
          outputRow = L.KernelIndexExpr "shadow_output" "ix"
          loopy =
            L.Module
              [L.Intermediate output emptyProvenance]
              []
              ( L.Function
                  [(shadowedArray, "shadowed_input")]
                  [ L.ParKernel
                      "shadowed"
                      ix
                      [L.Unary Copy (L.KernelVarExpr "ix") outputRow]
                      emptyProvenance
                  ]
                  "shadow_output"
              )
              []
              Nothing
      summaries <- case LA.kernelAccessSummaries loopy of
        Left err -> expectationFailure err
        Right value -> pure value
      let summary = M.lookup (LA.Time 0) summaries
      KernelAccess.kernelAllReadNames <$> summary `shouldBe` Just S.empty
      KernelAccess.kernelCodeReferenceNames <$> summary
        `shouldBe` Just (S.singleton "shadow_output")
      forceLoopyTron loopy
    describe "mixed-consumer buffer reuse" $ do
      it "reuses shared token and slot reads across routing identities" $ do
        let shared first second =
              either error id $
                T.normalizeConsumers
                  [ T.MatrixC 1
                  , T.ParC QBatchItems
                  , T.ParC $ QBatchItemsExpertPairs first 2
                  , T.ParC $ QBatchItemsExpertPairs second 4
                  ]
        mixedConsumersShareBuffer
          (shared "first" "second")
          (shared "second" "first")
          `shouldBe` Right True
      it "keeps incompatible shared token and slot channels separate" $ do
        let shared k =
              either error id $
                T.normalizeConsumers
                  [T.ParC QBatchItems, T.ParC $ QBatchItemsExpertPairs "routing" k]
        mixedConsumersShareBuffer
          (shared 2)
          (shared 4)
          `shouldBe` Right False
      it "reuses equal mixed channel contracts" $
        mixedConsumersShareBuffer
          (mixedConsumerFor 1 QBatchItems)
          (mixedConsumerFor 1 QBatchItems)
          `shouldBe` Right True
      it "ignores routing identity when the physical iteration space matches" $
        mixedConsumersShareBuffer
          ( mixedConsumerFor
              1
              (QBatchItemsExpertPairs ("first_routing" :: Name Loopy) 2)
          )
          ( mixedConsumerFor
              1
              (QBatchItemsExpertPairs ("second_routing" :: Name Loopy) 2)
          )
          `shouldBe` Right True
      it "does not reuse across different matrix participant counts" $
        mixedConsumersShareBuffer
          (mixedConsumerFor 1 QBatchItems)
          (mixedConsumerFor 2 QBatchItems)
          `shouldBe` Right False
      it "does not reuse across incompatible parallel iteration spaces" $
        mixedConsumersShareBuffer
          (mixedConsumerFor 1 QBatchItems)
          (mixedConsumerFor 1 $ Fin $ Static 2)
          `shouldBe` Right False
      it "does not reuse a mixed contract for a pure parallel contract" $
        mixedConsumersShareBuffer
          (mixedConsumerFor 1 QBatchItems)
          (T.ParC QBatchItems)
          `shouldBe` Right False
    it "generates distinct participants for two matrix and parallel readers" $ do
      let tron@(T.Module decls _ _ _ _ _ _) =
            LoopyTron.process mixedTwoMatrixConsumerModule
          cpp = renderCpp tron
          mixedChannels =
            [ (channel, info)
            | (channel, info) <- T.getChannels decls
            , T.channelConsumer info == mixedConsumerFor 2 QBatchItems
            ]
      (channel, _) <- case mixedChannels of
        [entry] -> pure entry
        entries ->
          expectationFailure $
            "expected one two-matrix mixed channel, got " ++ show entries
      let matrixParticipants =
            [ participant
            | T.MatmulLaunchStmt _ _ (inputChannel, participant) _ <- T.mainKernel tron
            , inputChannel == channel
            ]
          channelText = Txt.pack $ show channel
          call suffix = Txt.concat ["q_batch->", channelText, suffix]
          resetCall =
            Txt.concat [channelText, ".reset(n_workers, (2 + n_workers));"]
      matrixParticipants `shouldBe` [T.MatrixConsumerIndex 0, T.MatrixConsumerIndex 1]
      resetCall `shouldSatisfy` (`Txt.isInfixOf` cpp)
      call ".start_reading(0);" `shouldSatisfy` (`Txt.isInfixOf` cpp)
      call ".start_reading(1);" `shouldSatisfy` (`Txt.isInfixOf` cpp)
      call ".start_reading(2);" `shouldSatisfy` (`Txt.isInfixOf` cpp)
      call ".start_reading((2 + worker_ix));" `shouldSatisfy` (`Txt.isInfixOf` cpp)
      call ".start_reading_at(" `shouldSatisfy` (`Txt.isInfixOf` cpp)
    it "moeExample lowers to expected Tron" $ do
      let actual = TronTron.canonicalize $ LoopyTron.process L.moeExample
          expected = TronTron.canonicalize T.moeExample
      actual `shouldBe` expected
    it "generates routing from the indices buffer" $ do
      let cpp = renderCpp $ LoopyTron.process L.moeExample
      ("build_moe_routing_from_indices<8, 2>(indices" `Txt.isInfixOf` cpp)
        `shouldBe` True
      ("static constexpr size_t n_moe_routers = 1;" `Txt.isInfixOf` cpp)
        `shouldBe` True
    it "uses the declared routing when its name collides with a tensor" $ do
      let reserved = L.Variable "reserved" (L.Weight $ Shape [Static 1, Static 1]) Nothing
          func = L.moduleFunction L.moeExample
          addNestedRoutingLoop (L.ParKernel "activation" var body prov) =
            L.ParKernel "activation" var (body ++ [L.For expertIx []]) prov
          addNestedRoutingLoop stmt = stmt
          loopy =
            L.moeExample
              { L.moduleEnv =
                  L.Load reserved (LoadSafetensors "routing") False emptyProvenance
                    : L.moduleEnv L.moeExample
              , L.moduleFunction =
                  func
                    { L.functionParams = []
                    , L.functionStmts =
                        L.ParKernel
                          "initialize"
                          ix
                          [L.Unary Copy (L.KernelLiteral $ Cpp.FloatLit 1) (L.KernelIndexExpr "ins" "ix")]
                          emptyProvenance
                          : map addNestedRoutingLoop (drop 1 $ L.functionStmts func)
                    }
              }
          tron = LoopyTron.process loopy
          cpp = renderCpp tron
      LoopyCheck.check LoopyCheck.EscapesForbidden loopy `shouldBe` []
      case T.getMoeRoutings $ T.modDecls tron of
        [(routing, _)] -> do
          routing `shouldNotBe` "routing"
          [ iterSpace
            | (_, kernel) <- T.getKernels $ T.modDecls tron
            , T.For _ iterSpace _ <- T.kernelBody kernel
            ]
            `shouldBe` [QBatchItemsExpertPairs routing 2]
          let field = Txt.pack $ show routing
          cpp `shouldSatisfy` Txt.isInfixOf (field <> ".rows_in_expert_order().size()")
          cpp `shouldSatisfy` Txt.isInfixOf (field <> ".rows_in_expert_order()[row_ix]")
        _ -> expectationFailure "expected one routing object"
    it "publishes the routing schedule before launching its operations" $ do
      let cpp = renderCpp $ LoopyTron.process L.moeExample
      appearsInOrder
        [ "build_moe_routing_from_indices<8, 2>(indices"
        , "moe_router_0_schedule ="
        , "make_expert_matmul_schedule("
        , "model.model_experts____w1_weight"
        , "model.model_experts____w2_weight"
        , "routing_channel.finish_writing(0)"
        , "model.model_experts____w1_weight.template prepare_and_launch"
        , "moe_router_0_schedule.jobs_for(expert_matmul_id{0}), ins_view"
        , "model.model_experts____w2_weight.template prepare_and_launch"
        , "moe_router_0_schedule.jobs_for(expert_matmul_id{1})"
        ]
        cpp
        `shouldBe` True
    it "stripes flat expert-major rows across MoE body workers" $ do
      let cpp = renderCpp $ LoopyTron.process L.moeExample
      appearsInOrder
        [ "for (size_t row_ix = actual_worker_ix; "
            <> "row_ix < routing.rows_in_expert_order().size(); row_ix += n_actual_workers)"
        , "token_slot_id<2> ix = routing.rows_in_expert_order()[row_ix];"
        ]
        cpp
        `shouldBe` True
    it "counts MoE routing operations" $ do
      let cpp = renderCpp $ LoopyTron.process $ moeRouterNumberingModule 7
      ("static constexpr size_t n_moe_routers = 2;" `Txt.isInfixOf` cpp)
        `shouldBe` True
    it "rejects duplicate MoE router IDs before C++ emission" $ do
      let route = case [stmt | stmt@T.MoeRouteStmt{} <- T.mainKernel T.moeExample] of
            [stmt] -> stmt
            _ -> error "T.moeExample must contain exactly one MoeRouteStmt"
          mod_ =
            T.moeExample
              { T.mainKernel = T.mainKernel T.moeExample ++ [route]
              }
      assertRenderFails "duplicate MoE router ID" mod_
    it "generates top-k metadata in MoE router order" $ do
      let cpp = renderCpp $ LoopyTron.process $ moeRouterNumberingModule 7
      ("indexed_vector<moe_router_id, size_t>" `Txt.isInfixOf` cpp)
        `shouldBe` True
      ("expert_routing_top_k_by_router = std::vector<size_t>{2, 3}" `Txt.isInfixOf` cpp)
        `shouldBe` True
    it "generated MoE routing applies the model routing override" $ do
      let cpp = renderCpp T.moeExample
      ("outer_state.model_ref.expert_routing_override_" `Txt.isInfixOf` cpp)
        `shouldBe` True
      ("static constexpr size_t n_moe_routers = 1;" `Txt.isInfixOf` cpp)
        `shouldBe` True
      ("expert_routing_override_for" `Txt.isInfixOf` cpp)
        `shouldBe` True
      ("moe_router_id{0}" `Txt.isInfixOf` cpp)
        `shouldBe` True
      ("expert_stats_.record_router(moe_router_id{0}" `Txt.isInfixOf` cpp)
        `shouldBe` True
    it "numbers MoE routers densely and independently of attention layers" $ do
      moeRouterIds (LoopyTron.process $ moeRouterNumberingModule 7)
        `shouldBe` [0, 1]
      let tronMod = LoopyTron.process $ moeRouterNumberingModule 42
          cpp = renderCpp tronMod
      moeRouterIds tronMod `shouldBe` [0, 1]
      ("static constexpr size_t n_moe_routers = 2;" `Txt.isInfixOf` cpp)
        `shouldBe` True
      ( "expert_stats_.record_router(moe_router_id{0}, routing_0)"
          `Txt.isInfixOf` cpp
        )
        `shouldBe` True
      ( "expert_stats_.record_router(moe_router_id{1}, routing_1)"
          `Txt.isInfixOf` cpp
        )
        `shouldBe` True
    it "classifies router, K/V projection, expert matrix, and auxiliary tensors" $ do
      let tronMod = LoopyTron.process moePlacementModule
          cpp = renderCpp tronMod
          compact = compactCpp cpp
          kindByKey =
            M.fromList
              [ (loadOpKey (T.loadOp info), T.tensorPlacementKind info)
              | (_, info) <- T.getTensors (T.modDecls tronMod)
              ]
      M.lookup "query_matrix.weight" kindByKey
        `shouldBe` Just T.OrdinaryTensor
      M.lookup "model.layers.11.mlp.experts.{}.bias" kindByKey
        `shouldBe` Just T.OrdinaryTensor
      M.lookup "key_matrix.weight" kindByKey
        `shouldBe` Just T.AttentionKeyProjectionTensor
      M.lookup "value_matrix.weight" kindByKey
        `shouldBe` Just T.AttentionValueProjectionTensor
      M.lookup "model.layers.11.mlp.gate.weight" kindByKey
        `shouldBe` Just T.MoeRouterTensor
      M.lookup "model.layers.11.mlp.experts.{}.w1.weight" kindByKey
        `shouldBe` Just (T.MoeMatmulWeightTensor (T.MoeRouterId 0))
      M.lookup "model.layers.11.mlp.experts.{}.w2.weight" kindByKey
        `shouldBe` Just (T.MoeMatmulWeightTensor (T.MoeRouterId 0))
      context "preserves distinct K/V placement roles regardless of names" $ do
        ( "hardware::tensor_placement_request::ordinary_tensor(\"query_matrix\")"
            `Txt.isInfixOf` cpp
          )
          `shouldBe` True
        ( "hardware::tensor_placement_request::attention_key_projection_tensor(\"key_matrix\")"
            `Txt.isInfixOf` cpp
          )
          `shouldBe` True
        ( "hardware::tensor_placement_request::attention_value_projection_tensor(\"value_matrix\")"
            `Txt.isInfixOf` cpp
          )
          `shouldBe` True
      context "keeps the checkpoint layer in expert tensor names" $
        Txt.count "model.layers.11.mlp.experts.{}" cpp `shouldBe` 3
      context "annotates only expert matrix requests with tensor coordinates" $
        Txt.count
          "expert_tensor_coordinate{expert_coordinate{moe_router_id{0},expert_id(e)},expert_tensor_id{"
          compact
          `shouldBe` 2
      context "assigns IDs by semantic use rather than checkpoint visitation" $
        appearsInOrder
          [ "fmt::format(\"model.layers.11.mlp.experts.{}.w2\",e),expert_tensor_coordinate{expert_coordinate{moe_router_id{0},expert_id(e)},expert_tensor_id{1}}"
          , "fmt::format(\"model.layers.11.mlp.experts.{}.w1\",e),expert_tensor_coordinate{expert_coordinate{moe_router_id{0},expert_id(e)},expert_tensor_id{0}}"
          ]
          compact
          `shouldBe` True
      context "uses the MoE matmul weight tensor constructor" $
        Txt.count
          "hardware::tensor_placement_request::moe_matmul_weight_tensor"
          cpp
          `shouldBe` 2
      context "keeps expert view tensor requests unannotated" $
        ( "hardware::tensor_placement_request::ordinary_tensor(fmt::format(\"model.layers.11.mlp.experts.{}.bias\", e))"
            `Txt.isInfixOf` cpp
        )
          `shouldBe` True
      context "renders the router tensor as a router placement request" $
        ( "hardware::tensor_placement_request::moe_router_tensor(\"model.layers.11.mlp.gate\")"
            `Txt.isInfixOf` cpp
        )
          `shouldBe` True
    it "reuses placement identity but separates operations sharing one expert weight" $ do
      let actual =
            LoopyTron.process $
              moeMultiUseLauncherModule $
                LoadExpertSafetensors 8 "model.experts.{}.good.weight"
          cpp = compactCpp $ renderCpp actual
      Txt.count "expert_tensor_id{0}" cpp `shouldBe` 1
      Txt.count "expert_tensor_id{1}" cpp `shouldBe` 0
      [T.moeMatmulId op | T.MoeMatmulPrepareAndLaunchStmt op <- T.mainKernel actual]
        `shouldBe` [T.ExpertMatmulId 0, T.ExpertMatmulId 1]
      case [T.moeMatmulTensor op | T.MoeMatmulPrepareAndLaunchStmt op <- T.mainKernel actual] of
        [weight, sameWeight] -> do
          weight `shouldBe` sameWeight
          let source = "model." <> Txt.pack (show weight)
          ("make_expert_matmul_schedule(routing," <> source <> "," <> source <> ")")
            `Txt.isInfixOf` cpp
            `shouldBe` True
        other -> expectationFailure $ "expected two matmul uses, got " ++ show other
    describe "configuration initialization" $ do
      it "lowers trace-time values to constexpr configuration" $
        configInitializationFor "dim" L.moeExample
          `shouldBe` Just
            (T.ConstexprValue $ Cpp.LiteralExpr $ Cpp.IntLit 512)
      it "rejects a configuration without a trace-time value" $
        shouldPanicContaining "has no trace-time value" $
          forceLoopyTronConfigs loopyWithMissingConfigValue
    it "preserves attention identity, operands, config, and provenance" $ do
      let tronMod = LoopyTron.process explicitAttentionModule
          cpp = renderCpp tronMod
          attentions = [attention | T.AttentionStmt attention <- T.mainKernel tronMod]
          preparations =
            [preparation | T.PrepareAttentionStmt preparation <- T.mainKernel tronMod]
      case (preparations, attentions) of
        ([prepare], [attention]) -> do
          T.prepareAttentionOpId prepare `shouldBe` T.AttentionOpId 0
          T.prepareAttentionModelLayer prepare `shouldBe` T.ModelLayerId 7
          T.prepareAttentionProvenance prepare `shouldBe` attentionProv
          T.attentionOpId attention `shouldBe` T.AttentionOpId 0
          T.attentionModelLayer attention `shouldBe` T.ModelLayerId 7
          T.attentionKvSlot attention `shouldBe` T.KvSlotId 7
          T.attentionKernel attention
            `shouldBe` T.AttentionKernelSpec
              (T.AttentionKernelId 0)
              ( T.AttentionGeometry
                  (Cpp.Var "n_heads")
                  (Cpp.Var "n_kv_heads")
                  (Cpp.Var "head_size")
              )
          T.attentionHardwareCapability attention
            `shouldBe` T.SoftwareAttentionOnly
          T.attentionQuery attention
            `shouldBe` "q"
          T.attentionKvWrite attention
            `shouldBe` Just
              ( T.AttentionKvWrite
                  "k"
                  "v"
              )
          T.attentionOutput attention
            `shouldBe` "attn_out"
          T.attentionConfig attention
            `shouldBe` T.AttentionConfig
              (SlidingWindow 128)
              (Just "self_attn_sinks_weight")
              0.125
          T.attentionProvenance attention `shouldBe` attentionProv
          T.attentionCacheTopology tronMod
            `shouldBe` T.uniformAttentionCacheTopology
          context "indexes retention by the operation's actual dense slot ID" $ do
            ( "auto retentions = tron::full_history_kv_slot_retentions<n_layers>()"
                `Txt.isInfixOf` cpp
              )
              `shouldBe` True
            ( "retentions[7] = tron::kv_slot_retention::sliding_window(128)"
                `Txt.isInfixOf` cpp
              )
              `shouldBe` True
            ( "tron::uniform_kv_cache<n_layers, tron::kv_geometry{n_kv_heads, head_size}, dim * sizeof(typename btensor_t<dim>::scalar), cache_slot_retentions>"
                `Txt.isInfixOf` cpp
              )
              `shouldBe` True
        _ ->
          expectationFailure $
            "expected one attention preparation and operation, got "
              ++ show (preparations, attentions)
    it "counts one K/V read when both operands name the same buffer" $ do
      let accesses =
            [ WritePrivateKv "kv" "kv"
            , WriteSharedKv (AttentionKvGroupId 0) "kv" "kv"
            ]
          kvUsage access = do
            LA.LivenessAnalysis usages <-
              either expectationFailure pure $
                LA.lifetimeAnalysis (const False) $
                  sameBufferKvAttentionModule access
            pure $ M.lookup "kv" usages
          expected =
            Just $
              LA.Usage $
                M.fromList
                  [ (LA.Time 1, LA.Write $ T.ParP QBatchItems)
                  , (LA.Time 2, LA.Read T.SingleHostC)
                  ]
      mapM kvUsage accesses `shouldReturn` replicate (length accesses) expected

      let tronMod =
            LoopyTron.process $
              sameBufferKvAttentionModule $
                WritePrivateKv "kv" "kv"
          kvWrites =
            [ kvWrite
            | T.AttentionStmt attention <- T.mainKernel tronMod
            , Just kvWrite <- [T.attentionKvWrite attention]
            ]
      kvWrites `shouldBe` [T.AttentionKvWrite "kv" "kv"]
      TronCheck.checkModule tronMod `shouldBe` Right ()
    it "preserves symbolic geometry when legacy Loopy JSON omits geometry" $ do
      let tronMod = LoopyTron.process legacyAttentionModule
          kernels =
            [ T.attentionKernel operation
            | T.AttentionStmt operation <- T.mainKernel tronMod
            ]
      kernels
        `shouldBe` [ T.AttentionKernelSpec
                       (T.AttentionKernelId 0)
                       ( T.AttentionGeometry
                           (Cpp.Var "n_heads")
                           (Cpp.Var "n_kv_heads")
                           (Cpp.Var "head_size")
                       )
                   ]
      T.attentionCacheTopology tronMod `shouldBe` T.uniformAttentionCacheTopology
    it "preserves legacy topology when only one attention omits geometry" $ do
      let mixedModule =
            queryOnlyGeometryModule
              { L.moduleFunction =
                  (L.moduleFunction queryOnlyGeometryModule)
                    { L.functionStmts =
                        map removeFirstGeometry $
                          L.functionStmts $
                            L.moduleFunction queryOnlyGeometryModule
                    }
              }
          removeFirstGeometry
            (L.Attention out q kvAccess 2 _ typ sinks scale prov) =
              L.Attention out q kvAccess 2 Nothing typ sinks scale prov
          removeFirstGeometry statement = statement
          tronMod = LoopyTron.process mixedModule
      T.attentionCacheTopology tronMod
        `shouldBe` T.UniformAttentionCache
          (Cpp.Var "n_layers")
          (Cpp.LiteralExpr $ Cpp.IntLit 1)
          (Cpp.LiteralExpr $ Cpp.IntLit 64)
    it "retains the uniform adapter for a dense literal writer schedule" $ do
      let denseModule =
            queryOnlyGeometryModule
              { L.moduleEnv = layerCount : L.moduleEnv queryOnlyGeometryModule
              , L.moduleFunction =
                  (L.moduleFunction queryOnlyGeometryModule)
                    { L.functionStmts =
                        map remapLayer $
                          L.functionStmts $
                            L.moduleFunction queryOnlyGeometryModule
                    }
              }
          layerCount =
            L.Config
              (L.Variable "configured_layers" L.IntType Nothing)
              ["num_hidden_layers"]
              (Just $ Cpp.IntLit 2)
              emptyProvenance
          remapLayer
            (L.Attention out q kvAccess layer geometry typ sinks scale prov) =
              L.Attention
                out
                q
                kvAccess
                (if layer == 2 then 0 else 1)
                geometry
                typ
                sinks
                scale
                prov
          remapLayer statement = statement
          tronMod = LoopyTron.process denseModule
          operations =
            [ operation
            | T.AttentionStmt operation <- T.mainKernel tronMod
            ]
      T.attentionCacheTopology tronMod
        `shouldBe` T.UniformAttentionCache
          (Cpp.Var "n_layers")
          (Cpp.LiteralExpr $ Cpp.IntLit 1)
          (Cpp.LiteralExpr $ Cpp.IntLit 64)
      map T.attentionModelLayer operations `shouldBe` map T.ModelLayerId [0, 1]
      map T.attentionKvSlot operations `shouldBe` map T.KvSlotId [0, 1]
    it "uses an explicit slot for a configured prefix of model layers" $ do
      let prefixModule =
            uniformExplicitAttentionModule
              { L.moduleEnv = layerCount : L.moduleEnv uniformExplicitAttentionModule
              , L.moduleFunction =
                  (L.moduleFunction uniformExplicitAttentionModule)
                    { L.functionStmts =
                        map moveToFirstLayer $
                          L.functionStmts $
                            L.moduleFunction uniformExplicitAttentionModule
                    }
              }
          layerCount =
            L.Config
              (L.Variable "configured_layers" L.IntType Nothing)
              ["num_hidden_layers"]
              (Just $ Cpp.IntLit 2)
              emptyProvenance
          moveToFirstLayer
            (L.Attention out q kvAccess _ geometry typ sinks scale prov) =
              L.Attention out q kvAccess 0 geometry typ sinks scale prov
          moveToFirstLayer statement = statement
          tronMod = LoopyTron.process prefixModule
      T.attentionCacheTopology tronMod
        `shouldBe` T.HeterogeneousAttentionCache
          [ T.AttentionCacheSlotSpec
              (T.KvSlotId 0)
              (Cpp.LiteralExpr $ Cpp.IntLit 1)
              (Cpp.LiteralExpr $ Cpp.IntLit 4)
          ]
    it "compacts a literal nonzero layer into an explicit KV slot" $ do
      let tronMod = LoopyTron.process uniformExplicitAttentionModule
          attentions =
            [attention | T.AttentionStmt attention <- T.mainKernel tronMod]
      case attentions of
        [attention] -> do
          T.attentionKernel attention
            `shouldBe` T.AttentionKernelSpec
              (T.AttentionKernelId 0)
              ( T.AttentionGeometry
                  (Cpp.LiteralExpr $ Cpp.IntLit 2)
                  (Cpp.LiteralExpr $ Cpp.IntLit 1)
                  (Cpp.LiteralExpr $ Cpp.IntLit 4)
              )
          T.attentionModelLayer attention `shouldBe` T.ModelLayerId 7
          T.attentionKvSlot attention `shouldBe` T.KvSlotId 0
          T.attentionHardwareCapability attention
            `shouldBe` T.KvSlotHardwareAttentionCandidate
          T.attentionCacheTopology tronMod
            `shouldBe` T.HeterogeneousAttentionCache
              [ T.AttentionCacheSlotSpec
                  (T.KvSlotId 0)
                  (Cpp.LiteralExpr $ Cpp.IntLit 1)
                  (Cpp.LiteralExpr $ Cpp.IntLit 4)
              ]
        _ -> expectationFailure $ "expected one attention operation, got " ++ show attentions
    it "compacts sparse literal layers when only query geometry varies" $ do
      let tronMod = LoopyTron.process queryOnlyGeometryModule
          attentions =
            [attention | T.AttentionStmt attention <- T.mainKernel tronMod]
          geometry queryHeads =
            T.AttentionGeometry
              (Cpp.LiteralExpr $ Cpp.IntLit queryHeads)
              (Cpp.LiteralExpr $ Cpp.IntLit 1)
              (Cpp.LiteralExpr $ Cpp.IntLit 64)
      map (T.attentionGeometry . T.attentionKernel) attentions
        `shouldBe` [geometry 8, geometry 16]
      map T.attentionModelLayer attentions `shouldBe` map T.ModelLayerId [2, 9]
      map T.attentionKvSlot attentions `shouldBe` map T.KvSlotId [0, 1]
      map T.attentionHardwareCapability attentions
        `shouldBe` [T.KvSlotHardwareAttentionCandidate, T.SoftwareAttentionOnly]
      T.attentionCacheTopology tronMod
        `shouldBe` T.HeterogeneousAttentionCache
          [ T.AttentionCacheSlotSpec
              (T.KvSlotId slot)
              (Cpp.LiteralExpr $ Cpp.IntLit 1)
              (Cpp.LiteralExpr $ Cpp.IntLit 64)
          | slot <- [0, 1]
          ]
    it "gates hardware when only query geometry differs from the standard" $ do
      let tronMod = LoopyTron.process sameKvAttentionModule
          operations =
            [ operation
            | T.AttentionStmt operation <- T.mainKernel tronMod
            ]
      T.attentionCacheTopology tronMod
        `shouldBe` T.HeterogeneousAttentionCache
          [ T.AttentionCacheSlotSpec
              (T.KvSlotId slot)
              (Cpp.LiteralExpr $ Cpp.IntLit 1)
              (Cpp.LiteralExpr $ Cpp.IntLit 64)
          | slot <- [0, 1]
          ]
      map (T.attentionKernelId . T.attentionKernel) operations
        `shouldBe` map T.AttentionKernelId [0, 1]
      map T.attentionModelLayer operations `shouldBe` map T.ModelLayerId [2, 9]
      map T.attentionKvSlot operations `shouldBe` map T.KvSlotId [0, 1]
      map T.attentionHardwareCapability operations
        `shouldBe` [T.KvSlotHardwareAttentionCandidate, T.SoftwareAttentionOnly]
    it "keeps a multi-operation attention schedule valid after optimization" $ do
      let lowered = LoopyTron.process sparseAttentionModule
          optimized = TronTron.process lowered
          attentions =
            [ ()
            | T.AttentionStmt _ <- T.mainKernel optimized
            ]
      length attentions `shouldBe` 2
      TronCheck.checkModule lowered `shouldBe` Right ()
      TronCheck.checkModule optimized `shouldBe` Right ()
    it "emits a barrier-phased worker job with a static operation index" $ do
      let cpp = renderCpp $ LoopyTron.process explicitAttentionModule
          geometry =
            "tron::attention_geometry{n_heads, "
              <> "tron::kv_geometry{n_kv_heads, head_size}}"
      ( "outer_state.wait_attention_job(q_batch->outer_batch, worker_ix);"
          `Txt.isInfixOf` cpp
        )
        `shouldBe` True
      ( "attention_binding{attention_op_id(0), model_layer_id(7), kv_slot_id(7)}"
          `Txt.isInfixOf` cpp
        )
        `shouldBe` True
      ( "outer_state.template run_attention_job<"
          `Txt.isInfixOf` cpp
        )
        `shouldBe` True
      ("attention_armed" `Txt.isInfixOf` cpp) `shouldBe` False
      ("attention_started" `Txt.isInfixOf` cpp) `shouldBe` False
      ("attention_completed" `Txt.isInfixOf` cpp) `shouldBe` False
      ("valid_attention_configuration" `Txt.isInfixOf` cpp)
        `shouldBe` True
      ( "tron::attention_operation_config{128,tron::attention_sink_id(0),0.125f}"
          `Txt.isInfixOf` compactCpp cpp
        )
        `shouldBe` True
      ("return n_attention_ops" `Txt.isInfixOf` cpp)
        `shouldBe` True
      ("attention_operation_prefix_size" `Txt.isInfixOf` cpp)
        `shouldBe` False
      ("q, q_batch->q_channel, attn_out, q_batch->attn_out_channel" `Txt.isInfixOf` cpp)
        `shouldBe` True
      -- Two save_k calls per KV-writing operation, one function on both sides
      -- (Note [Shared block save] in model.hpp). Main passes worker index 0 and
      -- the worker count of run(). It lets save_k share the store. The helpers
      -- pass their own worker index and the worker count of run_main_help.
      -- Every helper-side host kernel call also ends in "worker_ix, n_workers);".
      -- So the whole call text is checked.
      Txt.count "outer_state.template save_k<" cpp `shouldBe` 2
      ( (attentionCallPrefix "save_k" geometry 0 <> "q_batch->outer_batch,k,0,n_workers);")
          `Txt.isInfixOf` compactCpp cpp
        )
        `shouldBe` True
      ( ( attentionCallPrefix "save_k" geometry 0
            <> "q_batch->outer_batch,k,worker_ix,n_workers);"
        )
          `Txt.isInfixOf` compactCpp cpp
        )
        `shouldBe` True
      Txt.count "outer_state.template save_v" cpp `shouldBe` 1
      Txt.count "outer_state.template prepare_attention_job" cpp `shouldBe` 1
      Txt.count "outer_state.template launch_early_hw_attention" cpp `shouldBe` 1
      Txt.count "outer_state.template prepare_late_hw_attention" cpp `shouldBe` 1
      Txt.count "outer_state.template launch_late_hw_attention" cpp `shouldBe` 1
      mapM_
        ( \method ->
            (attentionCallPrefix method geometry 0 `Txt.isInfixOf` compactCpp cpp)
              `shouldBe` True
        )
        [ "prepare_attention_job"
        , "launch_early_hw_attention"
        , "save_k"
        , "save_v"
        , "prepare_late_hw_attention"
        , "launch_late_hw_attention"
        , "run_attention_job"
        ]
      ("attention_operations[0]" `Txt.isInfixOf` cpp) `shouldBe` False
      ("uniform_attention_binding" `Txt.isInfixOf` cpp)
        `shouldBe` False
    it "rejects runtime layer truncation for static operation schedules" $ do
      let cpp = renderCpp $ LoopyTron.process explicitAttentionModule
      ( "max_layers == -1 || max_layers == static_cast<int>(n_layers)"
          `Txt.isInfixOf` cpp
        )
        `shouldBe` True
      ( ( "outer_state.cfg.max_layers == -1 || "
            <> "outer_state.cfg.max_layers == static_cast<int>(n_layers)"
        )
          `Txt.isInfixOf` cpp
        )
        `shouldBe` True
      ( "Ingest-generated models do not support partial runtime layer truncation"
          `Txt.isInfixOf` cpp
        )
        `shouldBe` True
    -- See Note [Early and late hardware attention launch] in model.hpp.
    it "places early or late hardware preparation and launch around K/V saves" $ do
      let cpp = renderCpp $ LoopyTron.process explicitAttentionModule
      appearsInOrder
        [ "outer_state.template prepare_attention_job"
        , "outer_state.template launch_early_hw_attention"
        , "q_batch->k_channel.start_reading_at(task_ix);"
        , "outer_state.template save_k"
        , "q_batch->v_channel.start_reading_at(task_ix);"
        , "outer_state.template save_v"
        , "outer_state.template prepare_late_hw_attention"
        , "outer_state.template launch_late_hw_attention"
        ]
        cpp
        `shouldBe` True
      appearsInOrder
        [ "outer_state.wait_attention_job(q_batch->outer_batch, worker_ix);"
        , "outer_state.help_drain_gof(4);"
        , "outer_state.template run_attention_job"
        ]
        cpp
        `shouldBe` True
      ("outer_state.begin_attention_job" `Txt.isInfixOf` cpp) `shouldBe` False
    it "walks sparse diagnostic layers in explicit operation order" $ do
      let cpp = renderCpp $ LoopyTron.process sparseAttentionModule
          compact = compactCpp cpp
          geometry =
            "tron::attention_geometry{n_heads, "
              <> "tron::kv_geometry{n_kv_heads, head_size}}"
      ("static constexpr size_t n_attention_ops = 2;" `Txt.isInfixOf` cpp)
        `shouldBe` True
      appearsInOrder
        [ "outer_state.wait_attention_job(q_batch->outer_batch,worker_ix);"
        , attentionCallPrefix "run_attention_job" geometry 0
        , "outer_state.wait_attention_job(q_batch->outer_batch,worker_ix);"
        , attentionCallPrefix "run_attention_job" geometry 1
        ]
        compact
        `shouldBe` True
      mapM_
        (\binding -> (binding `Txt.isInfixOf` cpp) `shouldBe` True)
        [ "attention_binding{attention_op_id(0), model_layer_id(2), kv_slot_id(2)}"
        , "attention_binding{attention_op_id(1), model_layer_id(9), kv_slot_id(9)}"
        ]
      Txt.count "outer_state.template run_attention_job" cpp `shouldBe` 2
      Txt.count "outer_state.wait_attention_job" cpp `shouldBe` 2
      Txt.count "outer_state.template launch_early_hw_attention" cpp `shouldBe` 2
      Txt.count "outer_state.template prepare_late_hw_attention" cpp `shouldBe` 2
      Txt.count "outer_state.template launch_late_hw_attention" cpp `shouldBe` 2
      ("attention_operations[0]" `Txt.isInfixOf` cpp) `shouldBe` False
      ("attention_operations[1]" `Txt.isInfixOf` cpp) `shouldBe` False
    it "lowers heterogeneous operation geometry without a transitional cache" $ do
      let tronMod = LoopyTron.process heterogeneousAttentionModule
          operations =
            [ operation
            | T.AttentionStmt operation <- T.mainKernel tronMod
            ]
      map (T.attentionKernelId . T.attentionKernel) operations
        `shouldBe` map T.AttentionKernelId [0, 1, 2]
      map T.attentionKvSlot operations `shouldBe` map T.KvSlotId [0, 1, 2]
      map T.attentionHardwareCapability operations
        `shouldBe` replicate 3 T.SoftwareAttentionOnly
      case T.attentionCacheTopology tronMod of
        T.HeterogeneousAttentionCache slots -> length slots `shouldBe` 3
        topology ->
          expectationFailure $
            "expected heterogeneous cache, got " ++ show topology
    it "emits three geometry-specialized kernels and operation descriptors" $ do
      let base = LoopyTron.process heterogeneousAttentionModule
          geometry qHeads kvHeads size =
            T.AttentionGeometry
              (LiteralExpr $ IntLit qHeads)
              (LiteralExpr $ IntLit kvHeads)
              (LiteralExpr $ IntLit size)
          specialize attention =
            let kernelId = T.unAttentionOpId $ T.attentionOpId attention
                kernelGeometry = case kernelId of
                  0 -> geometry 8 1 64
                  1 -> geometry 12 2 128
                  2 -> geometry 16 4 256
                  _ -> error "unexpected attention operation"
                slot = case kernelId of
                  0 -> T.KvSlotId 2
                  1 -> T.KvSlotId 0
                  2 -> T.KvSlotId 1
                  _ -> error "unexpected attention operation"
             in attention
                  { T.attentionKernel =
                      T.AttentionKernelSpec
                        (T.AttentionKernelId kernelId)
                        kernelGeometry
                  , T.attentionKvSlot = slot
                  , T.attentionHardwareCapability = T.SoftwareAttentionOnly
                  }
          specialized =
            map
              ( \case
                  T.AttentionStmt attention -> T.AttentionStmt $ specialize attention
                  stmt -> stmt
              )
              (T.mainKernel base)
          topology =
            T.HeterogeneousAttentionCache
              [ T.AttentionCacheSlotSpec
                  (T.KvSlotId 0)
                  (LiteralExpr $ IntLit 2)
                  (LiteralExpr $ IntLit 128)
              , T.AttentionCacheSlotSpec
                  (T.KvSlotId 1)
                  (LiteralExpr $ IntLit 4)
                  (LiteralExpr $ IntLit 256)
              , T.AttentionCacheSlotSpec
                  (T.KvSlotId 2)
                  (LiteralExpr $ IntLit 1)
                  (LiteralExpr $ IntLit 64)
              ]
          heterogeneousModule =
            base
              { T.mainKernel = specialized
              , T.attentionCacheTopology = topology
              }
          cpp = renderCpp heterogeneousModule
          compact = compactCpp cpp
          operationGeometries =
            [ (0, "tron::attention_geometry{8, tron::kv_geometry{1, 64}}")
            , (1, "tron::attention_geometry{12, tron::kv_geometry{2, 128}}")
            , (2, "tron::attention_geometry{16, tron::kv_geometry{4, 256}}")
            ]
      TronCheck.checkChannelSync
        (T.modDecls heterogeneousModule)
        (T.mainKernel heterogeneousModule)
        `shouldBe` Right ()
      let wrongWidth =
            heterogeneousModule
              { T.modDecls =
                  T.modifyDecl
                    ("q0" :: Name ('Tron 'Buffer))
                    (\info -> info{T.bufferWidth = LiteralExpr $ IntLit 64})
                    (T.modDecls heterogeneousModule)
              }
      case TronCheck.checkChannelSync
        (T.modDecls wrongWidth)
        (T.mainKernel wrongWidth) of
        Left message -> message `shouldSatisfy` isInfixOf "does not match attention geometry width"
        Right () -> expectationFailure "expected an attention operand-width failure"
      let integerQuery =
            heterogeneousModule
              { T.modDecls =
                  T.modifyDecl
                    ("q0" :: Name ('Tron 'Buffer))
                    (\info -> info{T.bufferScalarType = IntScalar})
                    (T.modDecls heterogeneousModule)
              }
      case TronCheck.checkChannelSync
        (T.modDecls integerQuery)
        (T.mainKernel integerQuery) of
        Left message -> message `shouldSatisfy` isInfixOf "buffer must use real scalars"
        Right () -> expectationFailure "expected an attention scalar-type failure"
      mapM_
        (\entry -> (entry `Txt.isInfixOf` cpp) `shouldBe` True)
        [ "attention_kernel_id(0), tron::attention_geometry{8, tron::kv_geometry{1, 64}}"
        , "#include \"tron/models/heterogeneous_kv_cache.hpp\""
        , "attention_kernel_id(1), tron::attention_geometry{12, tron::kv_geometry{2, 128}}"
        , "attention_kernel_id(2), tron::attention_geometry{16, tron::kv_geometry{4, 256}}"
        , "attention_binding{attention_op_id(2), model_layer_id(11), kv_slot_id(1)}"
        , "tron::attention_hardware_capability::software_only"
        , "tron::kv_slot_spec{tron::kv_geometry{2, 128}, tron::kv_slot_retention::full_history()}"
        , "using cache_t = tron::heterogeneous_kv_cache<cache_slot_specs"
        , "assemble_attention_plan<tron::attention_geometry{8, tron::kv_geometry{1, 64}}"
        ]
      mapM_
        ( \(operationIx, geometry) ->
            mapM_
              ( \method ->
                  ( attentionCallPrefix method geometry operationIx
                      `Txt.isInfixOf` compact
                  )
                    `shouldBe` True
              )
              [ "prepare_attention_job"
              , "launch_early_hw_attention"
              , "save_k"
              , "save_v"
              , "prepare_late_hw_attention"
              , "launch_late_hw_attention"
              , "run_attention_job"
              ]
        )
        operationGeometries
      mapM_
        ( \operationIx ->
            ( Txt.concat ["attention_operations[", Txt.pack $ show operationIx, "]"]
                `Txt.isInfixOf` cpp
            )
              `shouldBe` False
        )
        [0 :: Int, 1, 2]
      Txt.count "tron::attention_kernel_spec{" cpp `shouldBe` 3
      Txt.count "tron::attention_operation_descriptor{" cpp `shouldBe` 3
      ("tron::uniform_kv_cache" `Txt.isInfixOf` cpp) `shouldBe` False
      let mismatchedTopology =
            T.HeterogeneousAttentionCache
              [ T.AttentionCacheSlotSpec
                  (T.KvSlotId 0)
                  (LiteralExpr $ IntLit 2)
                  (LiteralExpr $ IntLit 64)
              , T.AttentionCacheSlotSpec
                  (T.KvSlotId 1)
                  (LiteralExpr $ IntLit 4)
                  (LiteralExpr $ IntLit 256)
              , T.AttentionCacheSlotSpec
                  (T.KvSlotId 2)
                  (LiteralExpr $ IntLit 1)
                  (LiteralExpr $ IntLit 64)
              ]
      assertRenderFails
        "kernel geometry disagrees with KV slot"
        heterogeneousModule{T.attentionCacheTopology = mismatchedTopology}
      let hardwareOperation =
            map
              ( \case
                  T.AttentionStmt attention
                    | T.attentionOpId attention == T.AttentionOpId 0 ->
                        T.AttentionStmt
                          attention
                            { T.attentionHardwareCapability =
                                T.KvSlotHardwareAttentionCandidate
                            }
                  stmt -> stmt
              )
              (T.mainKernel heterogeneousModule)
          hardwareModule = heterogeneousModule{T.mainKernel = hardwareOperation}
      TronCheck.checkModule hardwareModule `shouldBe` Right ()
      ( "tron::attention_hardware_capability::kv_slot_candidate"
          `Txt.isInfixOf` renderCpp hardwareModule
        )
        `shouldBe` True
      let processedSharedModule = LoopyTron.process sharedAttentionModule
          readOnlyHardwareModule =
            processedSharedModule
              { T.mainKernel =
                  map
                    ( \case
                        T.AttentionStmt attention
                          | T.attentionOpId attention == T.AttentionOpId 1 ->
                              T.AttentionStmt $
                                attention
                                  { T.attentionHardwareCapability =
                                      T.KvSlotHardwareAttentionCandidate
                                  , T.attentionConfig =
                                      (T.attentionConfig attention)
                                        { T.attentionType = FullCausal
                                        }
                                  }
                        stmt -> stmt
                    )
                    (T.mainKernel processedSharedModule)
              }
      case TronCheck.checkModule readOnlyHardwareModule of
        Left message ->
          message `shouldSatisfy` isInfixOf "read-only attention operation"
        Right () -> expectationFailure "expected a hardware-without-writer failure"
    it "does not launch an attention service for a zero-attention program" $ do
      let cpp = renderCpp T.example
      ("static constexpr size_t n_attention_ops = 0;" `Txt.isInfixOf` cpp)
        `shouldBe` True
      ("const size_t n_attn_workers = 0;" `Txt.isInfixOf` cpp)
        `shouldBe` True
      ("assemble_attention_plan" `Txt.isInfixOf` cpp)
        `shouldBe` False
      ("run_attention_worker(q_batches" `Txt.isInfixOf` cpp)
        `shouldBe` False
    it "uses ordinary plugin buffers, channels, and worker-domain counts" $ do
      let tronMod = LoopyTron.process explicitAttentionModule
          cpp = renderCpp tronMod
          qInfo = T.readDecl "q_channel" $ T.modDecls tronMod
          kInfo = T.readDecl "k_channel" $ T.modDecls tronMod
          vInfo = T.readDecl "v_channel" $ T.modDecls tronMod
          outputInfo = T.readDecl "attn_out_channel" $ T.modDecls tronMod
      T.channelConsumer qInfo `shouldBe` T.WorkerC T.AttentionWorkers
      T.channelConsumer kInfo `shouldBe` T.SingleHostC
      T.channelConsumer vInfo `shouldBe` T.SingleHostC
      T.channelProducer outputInfo `shouldBe` T.WorkerP T.AttentionWorkers
      ("q_channel.reset(n_workers, n_attn_workers);" `Txt.isInfixOf` cpp)
        `shouldBe` True
      ("k_channel.reset(n_workers, 1);" `Txt.isInfixOf` cpp)
        `shouldBe` True
      ("v_channel.reset(n_workers, 1);" `Txt.isInfixOf` cpp)
        `shouldBe` True
      ("attn_out_channel.reset(n_attn_workers, n_workers);" `Txt.isInfixOf` cpp)
        `shouldBe` True
      mapM_
        (\alias -> (alias `Txt.isInfixOf` cpp) `shouldBe` False)
        [ "outer_state.qs_for_attn"
        , "outer_state.vo_from_attn"
        , "outer_batch.qs_for_attn_channel"
        , "outer_batch.vo_from_attn_channel"
        , "run_pre_attn"
        , "run_post_attn"
        ]
    it "streams single-host K/V and MoE indices per item" $ do
      let attentionCpp = renderCpp $ LoopyTron.process explicitAttentionModule
          moeMod = LoopyTron.process L.moeExample
          moeCpp = renderCpp moeMod
          indicesInfo = T.readDecl "indices_channel" $ T.modDecls moeMod
      ("tensor_latch<signaled_producer_t>> k_channel;" `Txt.isInfixOf` attentionCpp)
        `shouldBe` True
      ("tensor_latch<signaled_producer_t>> v_channel;" `Txt.isInfixOf` attentionCpp)
        `shouldBe` True
      ("tensor_latch<fallback_producer_t>> k_channel;" `Txt.isInfixOf` attentionCpp)
        `shouldBe` False
      T.channelConsumer indicesInfo `shouldBe` T.SingleHostC
      ("indices_channel.reset(n_workers, 1);" `Txt.isInfixOf` moeCpp)
        `shouldBe` True
      ("tensor_latch<signaled_producer_t>> indices_channel;" `Txt.isInfixOf` moeCpp)
        `shouldBe` True
    it "preserves readiness for a later external parallel read" $
      checkMixedMoeReadersShareChannel
    it "requires an explicit channel for single-host function inputs" $ do
      LA.channelRequirement
        LA.InputVar
        (LA.Usage $ M.singleton (LA.Time 0) $ LA.Read T.SingleHostC)
        `shouldBe` Left
          "Function input consumed by accelerator: [SingleHostC]"
    it "rejects writes to function inputs" $ do
      LA.channelRequirement LA.InputVar selfProducedEntryReadUsage
        `shouldBe` Left "Function input is written: [ParP QBatchItems]"
    it "rejects self-produced entry reads for internal and output buffers" $ do
      let expected =
            Left
              ( "Producer requires an entry read at [Time 0], which cannot be "
                  <> "satisfied by its own write"
              )
      LA.channelRequirement LA.NormalVar selfProducedEntryReadUsage
        `shouldBe` expected
      LA.channelRequirement LA.OutputVar selfProducedEntryReadUsage
        `shouldBe` expected
      let earlierProducer =
            LA.Usage $
              M.fromList
                [ (LA.Time 0, LA.Write $ T.ParP QBatchItems)
                , (LA.Time 1, LA.ReadWrite (T.ParP QBatchItems) (T.ParC QBatchItems))
                ]
      mapM_
        ( \role ->
            LA.channelRequirement role earlierProducer
              `shouldBe` Left "Multiple producers: [ParP QBatchItems,ParP QBatchItems]"
        )
        [LA.NormalVar, LA.OutputVar]
    it "emits a shared-slot operation without fabricated K/V writes" $ do
      let tronMod = LoopyTron.process sharedAttentionModule
          operations =
            [ operation
            | T.AttentionStmt operation <- T.mainKernel tronMod
            ]
          cpp = renderCpp tronMod
      TronCheck.checkModule tronMod `shouldBe` Right ()
      map T.attentionKvSlot operations `shouldBe` [T.KvSlotId 0, T.KvSlotId 0]
      map (isJust . T.attentionKvWrite) operations
        `shouldBe` [True, False]
      map (T.attentionType . T.attentionConfig) operations
        `shouldBe` [FullCausal, SlidingWindow 64]
      map T.attentionHardwareCapability operations
        `shouldBe` replicate 2 T.SoftwareAttentionOnly
      T.attentionCacheTopology tronMod
        `shouldBe` T.HeterogeneousAttentionCache
          [ T.AttentionCacheSlotSpec
              (T.KvSlotId 0)
              (LiteralExpr $ IntLit 1)
              (LiteralExpr $ IntLit 4)
          ]
      -- One main-side and one helper-side save_k call, for the operation that
      -- writes KV. The second operation shares the slot. It writes nothing. See
      -- Note [Shared block save] in model.hpp.
      Txt.count "outer_state.template save_k<" cpp `shouldBe` 2
      -- The shared module keeps the sparse module's K buffer "k".
      (",k,0,n_workers);" `Txt.isInfixOf` compactCpp cpp) `shouldBe` True
      (",k,worker_ix,n_workers);" `Txt.isInfixOf` compactCpp cpp) `shouldBe` True
      Txt.count "outer_state.template save_v" cpp `shouldBe` 1
      ("k2_channel" `Txt.isInfixOf` cpp) `shouldBe` False
      ("v2_channel" `Txt.isInfixOf` cpp) `shouldBe` False
      ( "attention_binding{attention_op_id(1), model_layer_id(9), kv_slot_id(2)}"
          `Txt.isInfixOf` cpp
        )
        `shouldBe` False
      ( "attention_binding{attention_op_id(1), model_layer_id(9), kv_slot_id(0)}"
          `Txt.isInfixOf` cpp
        )
        `shouldBe` True
      context "a full-history consumer retains its shared slot" $
        ( "tron::kv_slot_spec{tron::kv_geometry{1, 4}, tron::kv_slot_retention::full_history()}"
            `Txt.isInfixOf` cpp
        )
          `shouldBe` True
    it "uses the widest finite window for a shared slot" $ do
      let tronMod = LoopyTron.process sharedAttentionModule
          withFiniteWindows =
            tronMod
              { T.mainKernel = map setFiniteWindow $ T.mainKernel tronMod
              }
          setFiniteWindow (T.AttentionStmt operation) =
            T.AttentionStmt $
              operation
                { T.attentionConfig =
                    (T.attentionConfig operation)
                      { T.attentionType =
                          SlidingWindow $
                            case T.attentionOpId operation of
                              T.AttentionOpId 0 -> 64
                              T.AttentionOpId 1 -> 128
                              operationId -> error $ "unexpected attention operation " ++ show operationId
                      }
                }
          setFiniteWindow statement = statement
          cpp = renderCpp withFiniteWindows
      TronCheck.checkModule withFiniteWindows `shouldBe` Right ()
      ( "tron::kv_slot_spec{tron::kv_geometry{1, 4}, tron::kv_slot_retention::sliding_window(128)}"
          `Txt.isInfixOf` cpp
        )
        `shouldBe` True
    it "keeps shared slots dense across private writes and multiple readers" $ do
      let tronMod = LoopyTron.process denseSharedSlotModule
          operations =
            [ operation
            | T.AttentionStmt operation <-
                T.mainKernel tronMod
            ]
      map T.attentionKvSlot operations
        `shouldBe` map T.KvSlotId [0, 0, 0, 1]
      map (isJust . T.attentionKvWrite) operations
        `shouldBe` [True, False, False, True]
      map T.attentionHardwareCapability operations
        `shouldBe` replicate 4 T.SoftwareAttentionOnly
      case T.attentionCacheTopology tronMod of
        T.HeterogeneousAttentionCache specs ->
          map T.attentionCacheSlotId specs
            `shouldBe` map T.KvSlotId [0, 1]
        other -> expectationFailure $ "expected heterogeneous cache, got " <> show other
    it "fails closed when a shared-K/V reader precedes its publisher" $
      shouldPanicContaining "reader precedes publisher" $
        forceLoopyTron $
          mapSharedAttentionStatements reverse sharedAttentionModule
    it "fails closed on duplicate shared-K/V publishers" $
      shouldPanicContaining "duplicate shared attention KV publisher" $
        forceLoopyTron $
          mapSharedAttentionStatements duplicateReader sharedAttentionModule
    it "fails closed when shared-K/V geometry changes" $
      shouldPanicContaining "shared attention KV geometry mismatch" $
        forceLoopyTron $
          mapSharedAttentionStatements changeReaderGeometry sharedAttentionModule
    it "rejects a shared-slot read without an earlier writer" $ do
      let tronMod = LoopyTron.process explicitAttentionModule
          readOnly = tronMod{T.mainKernel = map makeReadOnly $ T.mainKernel tronMod}
      case TronCheck.checkChannelSync (T.modDecls readOnly) (T.mainKernel readOnly) of
        Left message -> message `shouldSatisfy` isInfixOf "without a writer"
        Right () -> expectationFailure "expected a missing KV-slot writer failure"
    it "rejects an invalid operation-local attention scale" $ do
      let tronMod = LoopyTron.process explicitAttentionModule
          invalidScale =
            map
              ( \case
                  T.AttentionStmt operation ->
                    T.AttentionStmt $
                      operation
                        { T.attentionConfig =
                            (T.attentionConfig operation){T.attentionScale = 0}
                        }
                  stmt -> stmt
              )
              (T.mainKernel tronMod)
      case TronCheck.checkChannelSync (T.modDecls tronMod) invalidScale of
        Left message -> message `shouldSatisfy` isInfixOf "attention scale"
        Right () -> expectationFailure "expected invalid attention-scale failure"
    it "rejects invalid operation-local sliding windows" $ do
      let tronMod = LoopyTron.process explicitAttentionModule
          withWindow window =
            map
              ( \case
                  T.AttentionStmt operation ->
                    T.AttentionStmt $
                      operation
                        { T.attentionConfig =
                            (T.attentionConfig operation)
                              { T.attentionType = SlidingWindow window
                              }
                        }
                  statement -> statement
              )
              (T.mainKernel tronMod)
      mapM_
        ( \window ->
            case TronCheck.checkChannelSync
              (T.modDecls tronMod)
              (withWindow window) of
              Left message ->
                message `shouldSatisfy` isInfixOf "representable as a C++ int"
              Right () -> expectationFailure "expected invalid sliding-window failure"
        )
        [0, 2147483648]
    it "validates attention sink declaration, storage, rank, width, and source" $ do
      let tronMod = LoopyTron.process uniformExplicitAttentionModule
          sinkName = "self_attn_sinks_weight" :: Name ('Tron 'Tensor)
          withSinkName name =
            tronMod
              { T.mainKernel =
                  map
                    ( \case
                        T.AttentionStmt operation ->
                          T.AttentionStmt $
                            operation
                              { T.attentionConfig =
                                  (T.attentionConfig operation)
                                    { T.attentionSinks = Just name
                                    }
                              }
                        statement -> statement
                    )
                    (T.mainKernel tronMod)
              }
          withSinkInfo update =
            tronMod
              { T.modDecls = T.modifyDecl sinkName update $ T.modDecls tronMod
              }
          invalidModules =
            [ (withSinkName "missing_sink", "undeclared sinks tensor")
            , (withSinkInfo (\info -> info{T.memorySpace = T.Device}), "host memory")
            ,
              ( withSinkInfo
                  ( \info ->
                      info
                        { T.shape =
                            [LiteralExpr $ IntLit 2, LiteralExpr $ IntLit 1]
                        }
                  )
              , "rank 1"
              )
            ,
              ( withSinkInfo
                  (\info -> info{T.shape = [LiteralExpr $ IntLit 3]})
              , "query-head count"
              )
            ,
              ( withSinkInfo
                  ( \info ->
                      info
                        { T.loadOp =
                            LoadExpertSafetensors 1 "expert.{}.attention_sinks.weight"
                        }
                  )
              , "dense tensor"
              )
            ]
      mapM_
        ( \(invalid, expected) ->
            case TronCheck.checkModule invalid of
              Left message -> message `shouldSatisfy` isInfixOf expected
              Right () -> expectationFailure $ "expected sink failure: " ++ expected
        )
        invalidModules
    it "rejects more than one writer for a shared KV slot" $ do
      let tronMod = LoopyTron.process sparseAttentionModule
          duplicateWriter =
            tronMod{T.mainKernel = map makeSecondWriterShare $ T.mainKernel tronMod}
      case TronCheck.checkChannelSync
        (T.modDecls duplicateWriter)
        (T.mainKernel duplicateWriter) of
        Left message -> message `shouldSatisfy` isInfixOf "more than one writer"
        Right () -> expectationFailure "expected a duplicate KV-slot writer failure"
    it "keys generated attention config by operation when layers repeat" $ do
      let tronMod = LoopyTron.process $ sinkedSparseAttentionModule [2]
          sameLayer =
            tronMod
              { T.mainKernel =
                  map
                    (selectSoftwareAttention . makeSecondUseFirstLayerAndDistinctSlot)
                    (T.mainKernel tronMod)
              , T.attentionCacheTopology =
                  T.HeterogeneousAttentionCache
                    [ T.AttentionCacheSlotSpec
                        (T.KvSlotId slot)
                        (LiteralExpr $ IntLit 1)
                        (LiteralExpr $ IntLit 4)
                    | slot <- [0 .. 3]
                    ]
              }
          cpp = renderCpp sameLayer
          compact = compactCpp cpp
      TronCheck.checkModule sameLayer `shouldBe` Right ()
      appearsInOrder
        [ "attention_binding{attention_op_id(0),model_layer_id(2),kv_slot_id(2)}"
        , "tron::attention_operation_config{std::nullopt,tron::attention_sink_id(0),0.5f}"
        , "attention_binding{attention_op_id(1),model_layer_id(2),kv_slot_id(3)}"
        , "tron::attention_operation_config{64,std::nullopt,0.5f}"
        ]
        compact
        `shouldBe` True
      Txt.count "tron::attention_sink_spec{" cpp `shouldBe` 1
      context "defaults unused declared slots to full-history retention" $ do
        Txt.count
          "tron::kv_slot_spec{tron::kv_geometry{1, 4}, tron::kv_slot_retention::full_history()}"
          cpp
          `shouldBe` 3
        Txt.count
          "tron::kv_slot_spec{tron::kv_geometry{1, 4}, tron::kv_slot_retention::sliding_window(64)}"
          cpp
          `shouldBe` 1
    it "requires fixed cache topology for a remapped KV slot" $ do
      let tronMod = LoopyTron.process explicitAttentionModule
          nonuniform =
            tronMod{T.mainKernel = map makeNonuniform $ T.mainKernel tronMod}
          fixedSlots =
            T.HeterogeneousAttentionCache
              [ T.AttentionCacheSlotSpec
                  (T.KvSlotId slot)
                  (Cpp.Var "n_kv_heads")
                  (Cpp.Var "head_size")
              | slot <- [0 .. 3]
              ]
          fixedNonuniform = nonuniform{T.attentionCacheTopology = fixedSlots}
      TronCheck.checkChannelSync (T.modDecls nonuniform) (T.mainKernel nonuniform)
        `shouldBe` Right ()
      assertRenderFails "use a heterogeneous cache" nonuniform
      ( "attention_binding{attention_op_id(0), model_layer_id(7), kv_slot_id(3)}"
          `Txt.isInfixOf` renderCpp fixedNonuniform
        )
        `shouldBe` True
    it "rejects an attention operation without its matched preparation" $ do
      let tronMod = LoopyTron.process explicitAttentionModule
          withoutPrepare =
            filter (not . isAttentionPrepare) $ T.mainKernel tronMod
      case TronCheck.checkChannelSync (T.modDecls tronMod) withoutPrepare of
        Left message -> message `shouldSatisfy` isInfixOf "no matching attention preparation"
        Right () -> expectationFailure "expected unmatched attention preparation failure"
    it "rejects sparse or conflicting attention kernel registries" $ do
      let tronMod = LoopyTron.process sparseAttentionModule
          rewriteKernel f =
            map
              ( \case
                  T.AttentionStmt attention ->
                    T.AttentionStmt attention{T.attentionKernel = f attention}
                  stmt -> stmt
              )
              (T.mainKernel tronMod)
          sparseKernel attention
            | T.attentionOpId attention == T.AttentionOpId 1 =
                (T.attentionKernel attention)
                  { T.attentionKernelId = T.AttentionKernelId 2
                  }
            | otherwise = T.attentionKernel attention
          conflictingKernel attention
            | T.attentionOpId attention == T.AttentionOpId 1 =
                T.AttentionKernelSpec
                  (T.AttentionKernelId 0)
                  (T.AttentionGeometry "n_heads" "n_kv_heads" "different_head_size")
            | otherwise = T.attentionKernel attention
          duplicateWriter =
            map
              ( \case
                  T.AttentionStmt attention
                    | T.attentionOpId attention == T.AttentionOpId 1 ->
                        T.AttentionStmt attention{T.attentionKvSlot = T.KvSlotId 2}
                  stmt -> stmt
              )
              (T.mainKernel tronMod)
          expectFailure needle stmts =
            case TronCheck.checkChannelSync (T.modDecls tronMod) stmts of
              Left message -> message `shouldSatisfy` isInfixOf needle
              Right () -> expectationFailure $ "expected " ++ needle
      expectFailure "not dense from zero" $ rewriteKernel sparseKernel
      expectFailure "conflicting geometry" $ rewriteKernel conflictingKernel
      expectFailure "more than one writer" duplicateWriter
    it "shares routing storage while keeping schedules and weights local to each router" $ do
      let actual =
            LoopyTron.process $
              moeLauncherReuseModule
                (LoadExpertSafetensors 8 "model.experts.{}.second.weight")
                "second_routing"
          decls = T.modDecls actual
          operations = [op | T.MoeMatmulPrepareAndLaunchStmt op <- T.mainKernel actual]
      map fst (T.getMoeRoutings decls) `shouldBe` ["routing"]
      [(field, routerId) | T.MoeRouteStmt field _ routerId _ <- T.mainKernel actual]
        `shouldBe` [("routing", T.MoeRouterId 0), ("routing", T.MoeRouterId 1)]
      map T.moeMatmulRouterId operations `shouldBe` [T.MoeRouterId 0, T.MoeRouterId 1]
      [ T.tensorPlacementKind $ T.readDecl (T.moeMatmulTensor op) decls
        | op <- operations
        ]
        `shouldBe` [T.MoeMatmulWeightTensor (T.MoeRouterId 0), T.MoeMatmulWeightTensor (T.MoeRouterId 1)]
      Txt.count " = make_expert_matmul_schedule(" (renderCpp actual) `shouldBe` 2
    it "logits scale propagates from Loopy to Tron" $ do
      let munge = Just (LogitsScale BinaryDiv 16.0)
          loopyMod = L.moeExample{L.moduleLogitsMunge = munge}
          tronMod = LoopyTron.process loopyMod
      T.logitsMunge tronMod `shouldBe` munge
    it "logits softcap propagates from Loopy to Tron" $ do
      let munge = Just (LogitsSoftcap 30.0 Nothing)
          tronMod = LoopyTron.process L.moeExample{L.moduleLogitsMunge = munge}
      T.logitsMunge tronMod `shouldBe` munge
    it "preserves simultaneous input-token remappings through C++" $ do
      let remappings = [InputTokenRemapping 1 2, InputTokenRemapping 2 3]
          loopyMod = L.moeExample{L.moduleInputTokenRemappings = remappings}
          tronMod = LoopyTron.process loopyMod
          cpp = renderCpp tronMod
      T.inputTokenRemappings tronMod `shouldBe` remappings
      context "both conditions inspect the original token" $
        ( "return ((token == 1) ? 2 : ((token == 2) ? 3 : token));"
            `Txt.isInfixOf` cpp
        )
          `shouldBe` True
    it "carries Gemma-4 remapping and partial RoPE into one C++ artifact" $ do
      let parameters = Rope.RopeParameters 1000000 Rope.RopeScalingSimple
          remappings =
            [ InputTokenRemapping 258880 0
            , InputTokenRemapping 258881 0
            , InputTokenRemapping 258884 0
            ]
          loopyMod =
            (ropeConfigModule Nothing [(parameters, 512, 128)])
              { L.moduleInputTokenRemappings = remappings
              }
          tronMod = LoopyTron.process loopyMod
          configs = T.getConfigs $ T.modDecls tronMod
          ropeType =
            Cpp.LiteralType
              "rope_cfg<rope_layout::huggingface, 512, rope_scaling::simple, 128>"
          remappingCpp =
            "return ((token == 258880) ? 0 : ((token == 258881) ? 0 : "
              <> "((token == 258884) ? 0 : token)));"
          cpp = renderCpp tronMod
      T.inputTokenRemappings tronMod `shouldBe` remappings
      (T.configType <$> lookup "rope_config_0" configs) `shouldBe` Just ropeType
      remappingCpp `Txt.isInfixOf` cpp `shouldBe` True
      "rope_cfg<rope_layout::huggingface, 512, rope_scaling::simple, 128>"
        `Txt.isInfixOf` cpp
        `shouldBe` True
    it "rejects invalid programmatic input-token remappings" $ do
      let loopyMod =
            L.moeExample
              { L.moduleInputTokenRemappings =
                  [InputTokenRemapping 1 2, InputTokenRemapping 1 3]
              }
      assertRenderFails "duplicate source token IDs" $ LoopyTron.process loopyMod
    it "absent logits scale stays absent (regression)" $
      -- L.moeExample carries no logits munge; it must not appear in Tron.
      T.logitsMunge (LoopyTron.process L.moeExample) `shouldBe` Nothing
    describe "typed RoPE configuration" $ do
      it "emits complete Llama3 constructor arguments" $ do
        let parameters =
              Rope.RopeParameters 500000 $
                Rope.RopeScalingLlama3 $
                  Rope.Llama3RopeParameters 8 1 4 8192
            cpp =
              renderCpp $
                LoopyTron.process $
                  ropeConfigModule (Just 500000) [(parameters, 128, 128)]
            initializer =
              "rope_config_0(500000.0f, "
                <> "llama3_rope_scaling_params{8.0f, 1.0f, 4.0f, 8192.0f})"
        ( "rope_cfg<rope_layout::huggingface, 128, rope_scaling::llama3>"
            `Txt.isInfixOf` cpp
          )
          `shouldBe` True
        initializer `Txt.isInfixOf` cpp `shouldBe` True
      it "accepts repeated parameters with distinct rotary dimensions" $ do
        let parameters = Rope.RopeParameters 10000 Rope.RopeScalingSimple
            configs =
              T.getConfigs $
                T.modDecls $
                  LoopyTron.process $
                    ropeConfigModule
                      (Just 10000)
                      [(parameters, 64, 64), (parameters, 128, 128)]
            configType name = T.configType <$> lookup name configs
        configType "rope_config_0"
          `shouldBe` Just
            ( Cpp.LiteralType
                "rope_cfg<rope_layout::huggingface, 64, rope_scaling::simple>"
            )
        configType "rope_config_1"
          `shouldBe` Just
            ( Cpp.LiteralType
                "rope_cfg<rope_layout::huggingface, 128, rope_scaling::simple>"
            )
      it "emits a distinct active rotary template argument" $ do
        let parameters = Rope.RopeParameters 1000000 Rope.RopeScalingSimple
            configs =
              T.getConfigs $
                T.modDecls $
                  LoopyTron.process $
                    ropeConfigModule Nothing [(parameters, 512, 128)]
        (T.configType <$> lookup "rope_config_0" configs)
          `shouldBe` Just
            ( Cpp.LiteralType
                "rope_cfg<rope_layout::huggingface, 512, rope_scaling::simple, 128>"
            )
      it "emits independent heterogeneous configurations" $ do
        let llama theta factor =
              Rope.RopeParameters theta $
                Rope.RopeScalingLlama3 $
                  Rope.Llama3RopeParameters factor 1 4 8192
            linear =
              Rope.RopeParameters 10000 $ Rope.RopeScalingLinear 8
            cpp =
              renderCpp $
                LoopyTron.process $
                  ropeConfigModule
                    (Just 12345)
                    [(llama 500000 8, 128, 128), (linear, 64, 64)]
        "rope_config_0(500000.0f, llama3_rope_scaling_params{"
          `Txt.isInfixOf` cpp
          `shouldBe` True
        "rope_config_1(10000.0f, 8.0f)"
          `Txt.isInfixOf` cpp
          `shouldBe` True
      it "does not require a model-wide theta configuration" $ do
        let parameters = Rope.RopeParameters 10000 Rope.RopeScalingSimple
            cpp =
              renderCpp $
                LoopyTron.process $
                  ropeConfigModule Nothing [(parameters, 64, 64)]
        "rope_config_0(10000.0f)" `Txt.isInfixOf` cpp `shouldBe` True
      it "emits complete YaRN constructor arguments" $ do
        let parameters =
              Rope.RopeParameters 1000000 $
                Rope.RopeScalingYarn $
                  Rope.YarnRopeParameters 4 1.2 32 1 32768 True
            cpp =
              renderCpp $
                LoopyTron.process $
                  ropeConfigModule Nothing [(parameters, 128, 128)]
            initializer =
              "rope_config_0(1000000.0f, "
                <> "yarn_rope_scaling_params{4.0f, 1.2f, 32.0f, 1.0f, "
                <> "32768.0f, true})"
        initializer `Txt.isInfixOf` cpp `shouldBe` True
    it "logits div lowers to multiply-by-reciprocal in C++" $ do
      let cpp = renderCpp T.example{T.logitsMunge = Just (LogitsScale BinaryDiv 16.0)}
      -- 1/16 is exactly representable, so a power-of-two div emits a
      -- multiply by the exact reciprocal (0.0625).
      context "patch_logits multiplies by 6.25e-2f" $
        ("(logits_in * 6.25e-2f)" `Txt.isInfixOf` cpp) `shouldBe` True
    it "zero logits divisor fails before C++ emission" $
      assertRenderFails
        "divisor must be nonzero"
        T.example{T.logitsMunge = Just (LogitsScale BinaryDiv 0.0)}
    it "NaN logits scale fails before C++ emission" $
      assertRenderFails
        "logits scale must be finite"
        T.example{T.logitsMunge = Just (LogitsScale BinaryMul (0 / 0))}
    it "logits softcap lowers directly into both C++ hooks" $ do
      let cpp = renderCpp T.example{T.logitsMunge = Just (LogitsSoftcap 30.0 Nothing)}
      context "patch_logits emits the complete softcap expression" $
        ( "logits_out.set((tanh((logits_in / 30.0f)) * 30.0f));"
            `Txt.isInfixOf` cpp
        )
          `shouldBe` True
      context "patch_logits_in_place emits the complete softcap expression" $
        ("logits.set((tanh((logits / 30.0f)) * 30.0f));" `Txt.isInfixOf` cpp)
          `shouldBe` True
      ("final_logit_softcapping" `Txt.isInfixOf` cpp) `shouldBe` False
    it "invalid logits softcap fails before C++ emission" $
      assertRenderFails
        "softcap must be finite and positive"
        T.example{T.logitsMunge = Just (LogitsSoftcap 0.0 Nothing)}
    it "only tanh GELU reaches the device kernel" $ do
      let cpp = renderCpp $ LoopyTron.process $ unaryOpModule GeLUTanh
      ("tron::gelu_tanh" `Txt.isInfixOf` cpp) `shouldBe` True
      assertRenderFails
        "exact GELU has no device implementation"
        (LoopyTron.process $ unaryOpModule GeLU)
    it "default model emits an identity logits patch" $ do
      let cpp = renderCpp T.example
      context "reports no MoE routers" $
        ("static constexpr size_t n_moe_routers = 0;" `Txt.isInfixOf` cpp)
          `shouldBe` True
      context "patch_logits is the identity stub" $
        ("logits_out.set(logits_in);" `Txt.isInfixOf` cpp) `shouldBe` True
    it "emits operation-owned attention config without duplicate storage" $ do
      let cpp = renderCpp windowedModule
      context "plugin does not embed self_attention<model>" $
        ("self_attention<model" `Txt.isInfixOf` cpp) `shouldBe` False
      context "descriptor owns the sliding window, sink, and scale" $
        ( "tron::attention_operation_config{128,tron::attention_sink_id(0),0.125f}"
            `Txt.isInfixOf` compactCpp cpp
        )
          `shouldBe` True
      context "plugin has no generated layer configuration" $
        ("attn_layer_config" `Txt.isInfixOf` cpp) `shouldBe` False
      context "plugin has no model-global sink flag" $
        ("static constexpr bool attn_sinks" `Txt.isInfixOf` cpp) `shouldBe` False
      context "plugin has no generated layers array" $
        ("std::array<layer, n_layers> layers" `Txt.isInfixOf` cpp) `shouldBe` False
      context "sink accessor reuses the declared tensor" $
        ( "return std::span<const float>{self_attn_sinks_weight.data};"
            `Txt.isInfixOf` cpp
        )
          `shouldBe` True
      Txt.count "model.layers.7.self_attn.sinks" cpp `shouldBe` 1
    it "emits mixed sink schedules in either operation order" $ do
      let checkOrder sinkLayers expectedOrder = do
            let cpp = renderCpp $ LoopyTron.process $ sinkedSparseAttentionModule sinkLayers
                compact = compactCpp cpp
            appearsInOrder expectedOrder compact `shouldBe` True
            Txt.count "tron::attention_sink_spec{" cpp `shouldBe` 1
            Txt.count "shared.attn.sinks" cpp `shouldBe` 1
            Txt.count "return std::span<const float>{shared_attn_sinks_weight.data};" cpp
              `shouldBe` 1
      checkOrder
        [2]
        [ "tron::attention_operation_config{std::nullopt,tron::attention_sink_id(0),0.5f}"
        , "tron::attention_operation_config{64,std::nullopt,0.5f}"
        ]
      checkOrder
        [9]
        [ "tron::attention_operation_config{std::nullopt,std::nullopt,0.5f}"
        , "tron::attention_operation_config{64,tron::attention_sink_id(0),0.5f}"
        ]
    it "maps each sink ID to its tensor field" $ do
      let cpp = compactCpp $ renderCpp $ LoopyTron.process distinctSinkSparseAttentionModule
      appearsInOrder
        [ "if(id.i==0){returnstd::span<constfloat>{shared_attn_sinks_weight.data};}"
        , "if(id.i==1){returnstd::span<constfloat>{second_attn_sinks_weight.data};}"
        ]
        cpp
        `shouldBe` True
    it "keeps all-sink and no-sink generated registries explicit" $ do
      let allSinkCpp =
            renderCpp $ LoopyTron.process $ sinkedSparseAttentionModule [2, 9]
          noSinkCpp = renderCpp $ LoopyTron.process sparseAttentionModule
      Txt.count "attention_sink_id(0)" allSinkCpp `shouldBe` 3
      Txt.count "shared.attn.sinks" allSinkCpp `shouldBe` 1
      ("std::array<tron::attention_sink_spec, 0>" `Txt.isInfixOf` noSinkCpp)
        `shouldBe` True
    it "declares a plugin-owned uniform cache topology" $ do
      let cpp = renderCpp T.example
      context "owns the cache and its value geometry" $
        ( "using cache_t = tron::uniform_kv_cache<n_layers, "
            `Txt.isInfixOf` cpp
        )
          `shouldBe` True
      context "passes geometry as a value" $
        ("tron::kv_geometry{n_kv_heads, head_size}" `Txt.isInfixOf` cpp)
          `shouldBe` True
      context "does not duplicate the cache-owned slot descriptors" $
        ("static constexpr auto kv_slot_specs" `Txt.isInfixOf` cpp)
          `shouldBe` False
      context "does not reconstruct cache topology from layer kinds" $
        ("mixer_kind" `Txt.isInfixOf` cpp) `shouldBe` False
    it "compensated wcls visit emits the resolved head key" $ do
      -- The frontend aliases the tied head to its input embedding key, so
      -- visit_named_tensors puts that key in a placement request; the
      -- tie_word_embeddings parameter is unused.
      let cpp = renderCpp exampleWithWcls
      context "takes the compensated-tensor branch" $
        ("tron::compensated_tensor" `Txt.isInfixOf` cpp) `shouldBe` True
      context "emits the resolved head key" $
        ("\"model.embed_tokens\"" `Txt.isInfixOf` cpp) `shouldBe` True
      context "emits a tensor placement request" $
        ( "hardware::tensor_placement_request::ordinary_tensor(\"model.embed_tokens\")"
            `Txt.isInfixOf` cpp
        )
          `shouldBe` True
    it "slice codegen keeps typed batch row for sub-row slices" $ do
      let cpp = render $ TronCpp.process "slice_smoke" TE.Plain $ LoopyTron.process sliceModule
          need s =
            context
              ("rendered C++ did not contain " ++ show s ++ ":\n" ++ cpp)
              (cpp `shouldSatisfy` isInfixOf s)
      need "outer_state.input[ix]"
      need "output[ix]"
      need "tron::slice<256>()"
      need ".set("
      context
        ("rendered C++ used numeric token-job payload:\n" ++ cpp)
        (cpp `shouldSatisfy` (not . isInfixOf "ix.i"))
    it "weighted RMSNorm codegen accepts compatible sub-row slices" $ do
      let cpp =
            render $
              TronCpp.process "weighted_slice_rmsnorm" TE.Plain $
                LoopyTron.process weightedRmsNormSliceModule
          need s =
            context
              ("rendered C++ did not contain " ++ show s ++ ":\n" ++ cpp)
              (cpp `shouldSatisfy` isInfixOf s)
      need "tron::slice<256>()(outer_state.input[ix], (256 * h))"
      need "tron::slice<256>()(output[ix], (256 * h)).set("
      need "tron::rmsnorm(model.rms_w,"
    it "unit-weight RMSNorm codegen accepts sub-row slices" $ do
      let cpp =
            render $
              TronCpp.process "slice_rmsnorm" TE.Plain $
                LoopyTron.process unitRmsNormSliceModule
          need s =
            context
              ("rendered C++ did not contain " ++ show s ++ ":\n" ++ cpp)
              (cpp `shouldSatisfy` isInfixOf s)
      need "tron::slice<256>()"
      need "tron::rmsnorm("
      need ".set("
    it "shifted RMSNorm codegen passes a trailing unit offset" $ do
      let cpp =
            render $
              TronCpp.process "shifted_slice_rmsnorm" TE.Plain $
                LoopyTron.process shiftedRmsNormSliceModule
          compact = filter (`notElem` [' ', '\n']) cpp
      context
        ("rendered C++ omitted the shifted RMSNorm offset:\n" ++ cpp)
        (compact `shouldSatisfy` isInfixOf "1.0e-6f,1.0f)")
    it "residual RMSNorm fusion keeps compatible full rows fused" $ do
      let cpp =
            render $
              TronCpp.process "fused_rmsnorm" TE.Plain $
                LoopyTron.process $
                  residualRmsNormModule 256
          compact = filter (`notElem` [' ', '\n']) cpp
      context
        ("rendered C++ did not fuse residual RMSNorm:\n" ++ cpp)
        (cpp `shouldSatisfy` isInfixOf "tron::residual_and_rmsnorm(")
      context
        ("plain fused RMSNorm gained a weight offset:\n" ++ cpp)
        (compact `shouldSatisfy` (not . isInfixOf "1.0e-6f,1.0f"))
    it "shifted residual RMSNorm fusion preserves the static offset" $ do
      let cpp =
            render $
              TronCpp.process "shifted_fused_rmsnorm" TE.Plain $
                LoopyTron.process $
                  shiftedResidualRmsNormModule 256
          compact = filter (`notElem` [' ', '\n']) cpp
      context
        ("rendered C++ did not fuse shifted residual RMSNorm:\n" ++ cpp)
        (cpp `shouldSatisfy` isInfixOf "tron::residual_and_rmsnorm(")
      context
        ("rendered C++ omitted the shifted fused RMSNorm offset:\n" ++ cpp)
        (compact `shouldSatisfy` isInfixOf "1.0e-6f,1.0f)")
    it "residual RMSNorm fusion accepts compatible sub-row slices" $ do
      let cpp =
            render $
              TronCpp.process "fused_slice_rmsnorm" TE.Plain $
                LoopyTron.process $
                  residualRmsNormSliceModule 256
      context
        ("rendered C++ did not fuse sliced residual RMSNorm:\n" ++ cpp)
        (cpp `shouldSatisfy` isInfixOf "tron::residual_and_rmsnorm(")
    it "residual RMSNorm fusion declines a tail-width full row" $ do
      let cpp =
            render $
              TronCpp.process "tail_rmsnorm" TE.Plain $
                LoopyTron.process $
                  residualRmsNormModule 255
      context
        ("rendered C++ fused a tail-width residual RMSNorm:\n" ++ cpp)
        (cpp `shouldSatisfy` (not . isInfixOf "tron::residual_and_rmsnorm("))
      context
        ("rendered C++ omitted the tail-safe RMSNorm expression:\n" ++ cpp)
        (cpp `shouldSatisfy` isInfixOf "tron::rmsnorm(model.rms_w,")
    it "residual RMSNorm fusion uses the slice width for tail fallback" $ do
      let cpp =
            render $
              TronCpp.process "tail_slice_rmsnorm" TE.Plain $
                LoopyTron.process $
                  residualRmsNormSliceModule 255
      context
        ("rendered C++ fused a tail-width residual RMSNorm slice:\n" ++ cpp)
        (cpp `shouldSatisfy` (not . isInfixOf "tron::residual_and_rmsnorm("))
      context
        ("rendered C++ omitted the separate sliced Add:\n" ++ cpp)
        (cpp `shouldSatisfy` isInfixOf "tron::slice<255>()(residual[ix], 0).set(")
      context
        ("rendered C++ omitted the tail-safe sliced RMSNorm:\n" ++ cpp)
        ( cpp
            `shouldSatisfy` isInfixOf "tron::rmsnorm(model.rms_w, tron::slice<255>()(residual[ix], 0),"
        )
    it "scalar RMSNorm broadcasts its weight without residual fusion" $ do
      let cpp =
            render $
              TronCpp.process "scalar_rmsnorm" TE.Plain $
                LoopyTron.process $
                  scalarResidualRmsNormModule 2.0
          need s =
            context
              ("rendered C++ did not contain " ++ show s ++ ":\n" ++ cpp)
              (cpp `shouldSatisfy` isInfixOf s)
      need "(tron::rmsnorm(residual[ix], 1.0e-6f) * 2.0f)"
      context
        ("rendered C++ fused a scalar-weight RMSNorm:\n" ++ cpp)
        (cpp `shouldSatisfy` (not . isInfixOf "tron::residual_and_rmsnorm("))
    it "rejects a zero-rank tensor as an RMSNorm scalar" $
      assertRenderFails
        "RMSNorm weight must be a scalar C++ expression or a rank-1 tensor"
        (LoopyTron.process zeroRankTensorRmsNormModule)
    it "fuses a buffer-row RMSNorm weight" $ do
      let loopy = bufferWeightRmsNormModule False
      LoopyCheck.check LoopyCheck.EscapesForbidden loopy `shouldBe` []
      let cpp =
            render $
              TronCpp.process "buffer_row_rmsnorm" TE.Plain $
                LoopyTron.process loopy
      context
        ("rendered C++ did not fuse buffer-row RMSNorm weight:\n" ++ cpp)
        (cpp `shouldSatisfy` isInfixOf "tron::residual_and_rmsnorm(")
      context
        ("rendered C++ did not pass the buffer row as the fused weight:\n" ++ cpp)
        (cpp `shouldSatisfy` isInfixOf ", rms_weight[ix], 1.0e-6f)")
    it "fuses a sliced RMSNorm weight" $ do
      let loopy = bufferWeightRmsNormModule True
      LoopyCheck.check LoopyCheck.EscapesForbidden loopy `shouldBe` []
      let cpp =
            render $
              TronCpp.process "sliced_weight_rmsnorm" TE.Plain $
                LoopyTron.process loopy
      context
        ("rendered C++ did not fuse sliced RMSNorm weight:\n" ++ cpp)
        (cpp `shouldSatisfy` isInfixOf "tron::residual_and_rmsnorm(")
      context
        ("rendered C++ did not pass the slice as the fused weight:\n" ++ cpp)
        ( cpp
            `shouldSatisfy` isInfixOf
              ", tron::slice<256>()(rms_weight[ix], 0), 1.0e-6f)"
        )
    it "broadcasts a buffer-backed scalar RMSNorm weight" $ do
      LoopyCheck.check LoopyCheck.EscapesForbidden bufferScalarRmsNormModule
        `shouldBe` []
      let cpp =
            render $
              TronCpp.process "buffer_scalar_rmsnorm" TE.Plain $
                LoopyTron.process bufferScalarRmsNormModule
      context
        ("rendered C++ did not broadcast buffer-backed RMSNorm scalar:\n" ++ cpp)
        (cpp `shouldSatisfy` isInfixOf "* rms_scalars[ix][0]")
      context
        ("rendered C++ did not initialize the scalar buffer with sum:\n" ++ cpp)
        (cpp `shouldSatisfy` isInfixOf "tron::sum(input[ix])")
      context
        ("rendered C++ fused buffer-backed RMSNorm scalar:\n" ++ cpp)
        (cpp `shouldSatisfy` (not . isInfixOf "tron::residual_and_rmsnorm("))
    it "rejects a buffer-backed scalar weight for shifted RMSNorm codegen" $
      assertRenderFails
        "shifted RMSNorm weight must be a rank-1 tensor"
        (LoopyTron.process shiftedBufferScalarRmsNormModule)
    it "Cpp exprNames traverses lambdas without leaking binders" $ do
      let names =
            Cpp.exprNames $
              Cpp.Lambda
                [Cpp.CopyCapture "captured"]
                [Cpp.Param (Cpp.LiteralType "int") "arg"]
                ( Cpp.Block
                    [ Cpp.Declare
                        (Cpp.LiteralType "int")
                        "local"
                        (Just $ Cpp.Var "arg")
                    , Cpp.ExprStmt $
                        Cpp.BinOp
                          Cpp.Add
                          (Cpp.Var "captured")
                          (Cpp.Var "local")
                    , Cpp.ExprStmt $ Cpp.Var "outer"
                    ]
                )
      names `shouldBe` S.fromList [someCppName "captured", someCppName "outer"]
    it "reuses one launcher when same-shape matmul outputs share a buffer slot" $ do
      let actual = LoopyTron.process (launcherReuseModule True)
          launchers = map fst (T.getLaunchers (T.modDecls actual))
      sharedLauncher <- case launchers of
        [launcher] -> pure launcher
        other -> expectationFailure $ "expected one launcher, got " ++ show other
      denseLauncherUses actual `shouldBe` replicate 6 sharedLauncher
    it "keeps separate launchers when matmul outputs do not share a buffer slot" $ do
      let actual = LoopyTron.process (launcherReuseModule False)
      assertSeparateLaunchers actual
    it "keeps separate launchers for non-overlapping outputs without buffer-slot reuse" $ do
      let actual = LoopyTron.process launcherReuseWithoutSlotSharingModule
      assertSeparateLaunchers actual
    it "allocates a fresh launcher for each use of one matmul weight" $ do
      let actual = LoopyTron.process denseMultiUseLauncherModule
          (fills, prepares, launches) = denseLauncherPhases actual
      length (T.getLaunchers (T.modDecls actual)) `shouldBe` 2
      fills `shouldBe` prepares
      fills `shouldBe` launches
      case launches of
        [firstLauncher, secondLauncher] ->
          firstLauncher `shouldNotBe` secondLauncher
        other ->
          expectationFailure $ "expected two matmul launches, got " ++ show other
    it "counts a write-only output when classifying a reused matmul weight" $ do
      let mod_ = denseMultiUseDeadOutputLauncherModule
          function = L.moduleFunction mod_
      liveness <-
        either expectationFailure pure $ LA.lifetimeAnalysis (const False) mod_
      let assignment =
            BR.computeBufferAssignment
              BR.MidpointPrepares
              (L.moduleEnv mod_)
              (L.functionStmts function)
              liveness
              (L.functionReturn function)
      case assignment of
        Left err -> expectationFailure err
        Right (_, launchers, _, _, _) ->
          BR.launcherDisposition launchers "w1"
            `shouldBe` BR.FreshLauncherPerUse
    it "reuses one launcher when same-shape MoE matmul outputs share a buffer slot" $ do
      let actual =
            LoopyTron.process $
              moeLauncherReuseModule
                (LoadExpertSafetensors 8 "model.experts.{}.second.weight")
                "routing"
          launchers = map fst (T.getLaunchers (T.modDecls actual))
      sharedLauncher <- case launchers of
        [launcher] -> pure launcher
        other -> expectationFailure $ "expected one MoE launcher, got " ++ show other
      moeMatmulLaunchers actual `shouldBe` replicate 2 sharedLauncher
    describe "routing reuse analysis" $ do
      let allocate entries = do
            let env =
                  [ L.Intermediate
                      (L.Variable name (L.MoeRoutingType experts topK) Nothing)
                      emptyProvenance
                  | (name, (experts, topK), _) <- entries
                  ]
                usage (write, read) =
                  LA.Usage $
                    M.fromList
                      [ (LA.Time write, LA.Write T.MoeRoutingP)
                      , (LA.Time read, LA.Read T.MoeRoutingC)
                      ]
                liveness =
                  LA.LivenessAnalysis $
                    M.fromList [(name, usage lifetime) | (name, _, lifetime) <- entries]
            case BR.computeBufferAssignment
              BR.MidpointPrepares
              env
              []
              liveness
              "result" of
              Left err -> expectationFailure err
              Right (_, _, routings, prepares, _) -> pure (routings, prepares)
      it "plans a shared slot with preparation between routing lifetimes" $ do
        -- The owner follows execution order, including when declared last.
        (routings, prepares) <-
          allocate [("second", (8, 2), (24, 25)), ("first", (8, 2), (0, 1))]
        BR.canonicalRouting routings "first" `shouldBe` "first"
        BR.canonicalRouting routings "second" `shouldBe` "first"
        [time | (time, names) <- M.toList prepares, "second" `elem` names]
          `shouldSatisfy` \case
            [time] -> time > LA.Time 1 && time <= LA.Time 24
            _ -> False
      it "keeps overlapping routing lifetimes in separate slots" $ do
        (routings, _) <-
          allocate [("first", (8, 2), (0, 24)), ("second", (8, 2), (1, 25))]
        BR.canonicalRouting routings "first"
          `shouldNotBe` BR.canonicalRouting routings "second"
      it "keeps different routing shapes in separate slots" $
        mapM_
          ( \shape -> context ("second routing shape " ++ show shape) $ do
              (routings, _) <-
                allocate [("first", (8, 2), (0, 1)), ("second", shape, (24, 25))]
              BR.canonicalRouting routings "first"
                `shouldNotBe` BR.canonicalRouting routings "second"
          )
          [(16, 2), (8, 1)]
    it "keeps unguarded scratch separate for different routings" $ do
      let space routingName = QBatchItemsExpertPairs routingName 2
          usage routingName write read =
            LA.Usage $
              M.fromList
                [ (write, LA.Write $ T.ParP $ space routingName)
                , (read, LA.Read $ T.ParC $ space routingName)
                ]
          liveness secondRouting =
            LA.LivenessAnalysis $
              M.fromList
                [ ("a", usage "first_routing" (LA.Time 0) (LA.Time 1))
                , ("b", usage secondRouting (LA.Time 24) (LA.Time 25))
                ]
          env =
            [ L.Intermediate
                (L.Variable name (L.Array RealScalar (Just $ space "first_routing") (Static 4)) Nothing)
                emptyProvenance
            | name <- ["a", "b"]
            ]
          allocate secondRouting =
            case BR.computeBufferAssignment
              BR.MidpointPrepares
              env
              []
              (liveness secondRouting)
              "result" of
              Left err -> expectationFailure err
              Right (assignment, _, _, _, _) -> pure $ BR.unBufferAssignment assignment
      separate <- allocate "second_routing"
      separate M.! "a" `shouldNotBe` separate M.! "b"
      shared <- allocate "first_routing"
      shared M.! "a" `shouldBe` shared M.! "b"
    it "allocates a fresh launcher for each use of one MoE matmul weight" $ do
      let actual =
            LoopyTron.process $
              moeMultiUseLauncherModule $
                LoadExpertSafetensors 8 "model.experts.{}.good.weight"
      length (T.getLaunchers (T.modDecls actual)) `shouldBe` 2
      case moeMatmulLaunchers actual of
        [firstLauncher, secondLauncher] ->
          firstLauncher `shouldNotBe` secondLauncher
        other ->
          expectationFailure $ "expected two MoE matmul launches, got " ++ show other
    it "asserts expert tagging on a multi-use MoE weight" $
      shouldPanicContaining
        "frontend must tag stacked-expert"
        ( void $
            forceLoopyTron $
              moeMultiUseLauncherModule $
                LoadSafetensors "model.experts.good.weight"
        )
    it "asserts expert tagging on non-canonical reused MoE weights" $
      shouldPanicContaining
        "frontend must tag stacked-expert"
        ( void $
            forceLoopyTron $
              moeLauncherReuseModule (LoadSafetensors "model.experts.second.weight") "routing"
        )
    describe "host matrix-vector products" $ do
      let gateTensor tron =
            case [ (name, info)
                 | (name, info) <- T.getTensors (T.modDecls tron)
                 , T.loadOp info == LoadSafetensors "model.gate.weight"
                 ] of
              [entry] -> pure entry
              other ->
                expectationFailure $ "expected one gate tensor, got " ++ show other
          withGateSemantics =
            L.moeMatVecExample
              { L.moduleEnv = map tagGate (L.moduleEnv L.moeMatVecExample)
              }
          tagGate (L.Load var@L.Variable{L.name = "gate_w"} op compensated prov) =
            L.Load var{L.semantics = Just (Weight WeightRouter, 0)} op compensated prov
          tagGate stmt = stmt
      it "promotes a MatVec weight to an ordinary host matrix" $ do
        mapM_
          ( \loopy -> do
              (_, info) <- gateTensor $ LoopyTron.process loopy
              T.memorySpace info `shouldBe` T.HostMatrix
              T.tensorPlacementKind info `shouldBe` T.OrdinaryTensor
          )
          [L.moeMatVecExample, withGateSemantics]
      it "adds no LoopyCheck errors to moeExample" $
        LoopyCheck.check LoopyCheck.EscapesForbidden L.moeMatVecExample
          `shouldBe` LoopyCheck.check LoopyCheck.EscapesForbidden L.moeExample
      it "emits a weight_matrix owner, matvec call and load-time storage report" $ do
        let tron = LoopyTron.process L.moeMatVecExample
            cpp = renderCpp tron
        (gate, _) <- gateTensor tron
        let field = Txt.pack $ show gate
        mapM_
          (\needle -> cpp `shouldSatisfy` Txt.isInfixOf needle)
          [ "#include \"tron/tensor/weight_matrix.hpp\""
          , "weight_matrix<8, 512> " <> field <> "{uninitialized};"
          , "model." <> field <> ".matvec(gate_out[ix], ins[ix]);"
          , "hardware::tensor_placement_request::ordinary_tensor(\"model.gate\")"
          ]
        appearsInOrder
          [ "void finalize_weights() noexcept {"
          , "// See Note [HostMatrix weights] in ingest/src/Tron.hs."
          , "fp32_storage_log fp32_storage;"
          , "fp32_storage.add(\"model.gate\", " <> field <> ");"
          , "fp32_storage.report();"
          ]
          cpp
          `shouldBe` True
        cpp `shouldSatisfy` (not . Txt.isInfixOf "weight_storage::fp32")
      it "emits no matmul, launcher or channel for the gate" $ do
        let tron = LoopyTron.process L.moeMatVecExample
        (gate, _) <- gateTensor tron
        [() | T.MatmulFillStmt{} <- T.mainKernel tron] `shouldBe` []
        [() | T.MatmulPrepareStmt{} <- T.mainKernel tron] `shouldBe` []
        [() | T.MatmulLaunchStmt{} <- T.mainKernel tron] `shouldBe` []
        map fst (T.getLaunchers (T.modDecls tron))
          `shouldSatisfy` all (not . isInfixOf (show gate) . show)
        [ name
          | (name, info) <- T.getChannels (T.modDecls tron)
          , T.channelProducer info == T.ParP QBatchItems
          , T.channelConsumer info == T.ParC QBatchItems
          ]
          `shouldBe` []
      it "rejects a weight used by both a MatVec and a matmul" $ do
        let intermediate name =
              L.Intermediate
                ( L.Variable
                    name
                    (L.Array RealScalar (Just QBatchItems) (Static 8))
                    Nothing
                )
                emptyProvenance
            rowKernel name stmt =
              L.ParKernel
                name
                (L.Variable "ix" (L.LoopIxType QBatchItems) Nothing)
                [stmt]
                emptyProvenance
            row name = L.KernelIndexExpr name "ix"
            matVecKernel =
              rowKernel "matvec" $
                L.Binary
                  MatVec
                  (L.KernelVarExpr "gate_w")
                  (row "ins")
                  (row "gate_extra")
            matmulAndReader =
              [ L.Matmul "gate_extra" "gate_w" "ins" emptyProvenance
              , rowKernel "consume" $ L.Unary Copy (row "gate_extra") (row "gate_sink")
              ]
            append base names stmts =
              let func = L.moduleFunction base
               in base
                    { L.moduleEnv = L.moduleEnv base ++ map intermediate names
                    , L.moduleFunction =
                        func{L.functionStmts = L.functionStmts func ++ stmts}
                    }
        shouldPanicContaining "used by both a MatVec kernel and a matmul" $
          forceLoopyTron $
            append L.moeMatVecExample ["gate_extra", "gate_sink"] matmulAndReader
        shouldPanicContaining "is already a device tensor" $
          forceLoopyTron $
            append L.moeExample ["gate_extra"] [matVecKernel]
      it "warms router weights only in the MatVec kernel, before its first wait" $ do
        let tron = LoopyTron.process L.moeMatVecExample
            cpp = renderCpp tron
        (gate, _) <- gateTensor tron
        let touch = "model." <> Txt.pack (show gate) <> ".touch();"
        appearsInOrder
          [ "void kernel_matvec("
          , "size_t actual_worker_ix = (n_workers == 1) ? 0 : worker_ix - 1;"
          , "// See Note [MoE router warm-up] in ingest/src/TronCpp.hs."
          , "if (actual_worker_ix < q_batch->items.size() && "
              <> "q_batch->items.size() <= n_actual_workers) {"
          , touch
          , "q_batch->ins_channel.start_reading_at(actual_worker_ix);"
          , "TRACE_EVENT(\"model\", \"kernel_matvec\");"
          , "void kernel_topk_softmax("
          ]
          cpp
          `shouldBe` True
        Txt.count ".touch();" cpp `shouldBe` 1
      it "leaves modules without MatVec unchanged" $ do
        let cpp = renderCpp $ LoopyTron.process L.moeExample
        cpp `shouldSatisfy` Txt.isInfixOf "void finalize_weights() noexcept { }"
        cpp `shouldSatisfy` (not . Txt.isInfixOf "weight_matrix")
    describe "aligned lane domain" $ do
      let tron = LoopyTron.process L.laneDomainExample
          helpers = LoopyTron.processWith LoopyTron.HelperStripeOnly L.laneDomainExample
          kernelLanes =
            M.fromList
              [ (show name, T.kernelLanes info)
              | (name, info) <- T.getKernels (T.modDecls tron)
              ]
          blendLanes = [lanes | T.MoeBlendStmt _ _ _ _ _ lanes _ <- T.mainKernel tron]
          isLaneProducer = \case
            T.LaneP _ -> True
            _ -> False
          hasLaneConsumer consumer =
            not $ null [() | T.LaneConsumer _ <- NE.toList (T.consumerDomains consumer)]
          laneChannels m =
            [ (name, info)
            | (name, info) <- T.getChannels (T.modDecls m)
            , isLaneProducer (T.channelProducer info)
                || hasLaneConsumer (T.channelConsumer info)
            ]
          -- Text of one generated method, from its signature up to its closing
          -- brace.
          methodText name cpp =
            let (_, rest) = Txt.breakOn ("    void " <> name <> "(") cpp
             in fst (Txt.breakOn "\n    }\n" rest)
          cpp = renderCpp tron
          helpersCpp = renderCpp helpers
      it "holds the embedding and each layer's router, blend and next kernels" $ do
        M.filter (== T.AlignedLanes) kernelLanes
          `shouldBe` M.fromList
            [ (name, T.AlignedLanes)
            | name <-
                [ "kernel_embed"
                , "kernel_router_0"
                , "kernel_next_0"
                , "kernel_router_1"
                , "kernel_next_1"
                ]
            ]
        blendLanes `shouldBe` [T.AlignedLanes, T.AlignedLanes]
      it "keeps attention-input and expert-row kernels on the helper stripe" $
        [ kernelLanes M.! name
        | name <-
            [ "kernel_attn_in_0"
            , "kernel_attn_in_1"
            , "kernel_act_0"
            , "kernel_act_1"
            , "kernel_down_b_0"
            , "kernel_down_b_1"
            ]
        ]
          `shouldBe` replicate 6 T.HelperStripe
      it "gives the whole domain one stripe over QBatchItems" $
        [ T.kernelIterSpace info
        | (_, info) <- T.getKernels (T.modDecls tron)
        , T.kernelLanes info == T.AlignedLanes
        ]
          `shouldSatisfy` all (== QBatchItems)
      it "is empty without attention" $ do
        let noAttention = LoopyTron.process L.moeMatVecExample
        [ ()
          | (_, info) <- T.getKernels (T.modDecls noAttention)
          , T.kernelLanes info /= T.HelperStripe
          ]
          `shouldBe` []
        renderCpp noAttention `shouldSatisfy` (not . Txt.isInfixOf "n_attention_lanes")
      it "puts channels on five lane-side contracts, none between domain kernels" $ do
        let contract (_, info) =
              case (T.channelProducer info, T.channelConsumer info) of
                (T.MatrixP{}, T.LaneC QBatchItems) -> "o_proj output"
                (T.LaneP QBatchItems, T.MatrixC 1) -> "expert input"
                (T.LaneP QBatchItems, T.SingleHostC) -> "top-k indices"
                (T.ParP QBatchItemsExpertPairs{}, T.LaneC QBatchItems) -> "blend input"
                (T.LaneP QBatchItems, T.MatrixC 3) -> "QKV input"
                other -> "unexpected " ++ show other
        S.fromList (map contract $ laneChannels tron)
          `shouldBe` S.fromList
            [ "o_proj output"
            , "expert input"
            , "top-k indices"
            , "blend input"
            , "QKV input"
            ]
        [ name
          | (name, info) <- T.getChannels (T.modDecls tron)
          , T.channelProducer info == T.LaneP QBatchItems
          , T.channelConsumer info == T.LaneC QBatchItems
          ]
          `shouldBe` []
      it "gives a lane-written row read on the helper stripe a channel" $ do
        summaries <-
          either expectationFailure pure $ LA.kernelAccessSummaries L.laneDomainExample
        let routerTimes =
              [ t
              | (t, L.ParKernel name _ _ _) <-
                  zip [LA.Time 0 ..] $
                    L.functionStmts $
                      L.moduleFunction L.laneDomainExample
              , name == "router_0"
              ]
            LA.LivenessAnalysis usages =
              LA.lifetimeAnalysisWithKernelAccesses
                summaries
                (`elem` routerTimes)
                L.laneDomainExample
        LA.channelRequirement LA.NormalVar (usages M.! "mid_0")
          `shouldBe` Right (LA.NeedsChannel (T.LaneP QBatchItems) (T.ParC QBatchItems))
      it "counts attention lanes on exactly the lane channels" $ do
        let resetText = methodText "reset_channels" cpp
            laneNames =
              S.fromList [Txt.pack (show name) | (name, _) <- laneChannels tron]
            counted =
              S.fromList
                [ Txt.strip name
                | line <- Txt.lines resetText
                , "n_attention_lanes)" `Txt.isInfixOf` line
                , let (name, _) = Txt.breakOn ".reset(" line
                ]
        counted `shouldBe` laneNames
        S.size counted `shouldBe` 5
      it "resets like the helpers-only module when no attention worker joins" $ do
        -- Channels are declared in first-use order, which buffer reuse may
        -- change, so compare the resets as a set.
        let laneOnly line =
              any
                (`Txt.isInfixOf` line)
                [ "n_attention_lanes ="
                , "See Note [Aligned lane domain]"
                , "TRON_ASSERT(n_workers - 1 + n_attn_workers =="
                , "app_pool().num_workers(),"
                , "must fill the pool"
                , "Attention workers are the last pool workers"
                ]
            dropLanes =
              S.fromList
                . filter (not . laneOnly)
                . Txt.lines
                . Txt.replace "(n_workers + n_attention_lanes)" "n_workers"
        dropLanes (methodText "reset_channels" cpp)
          `shouldBe` S.fromList (Txt.lines $ methodText "reset_channels" helpersCpp)
      it "checks the pool split, then computes the join once, into the last member" $ do
        appearsInOrder
          [ "void reset_channels("
          , "// See Note [Aligned lane domain] in ingest/src/TronCpp.hs."
          , "TRON_ASSERT(n_workers - 1 + n_attn_workers =="
          , "app_pool().num_workers(),"
          , "n_attention_lanes = tron::attention_lanes_join(items.size(), n_workers, "
              <> "app_pool().num_workers()) ? n_attn_workers : 0;"
          , ".reset("
          ]
          cpp
          `shouldBe` True
        Txt.count "n_attention_lanes = tron" cpp `shouldBe` 1
        let batch =
              fst $
                Txt.breakOn "    plugin_batch(" $
                  snd $
                    Txt.breakOn "  struct plugin_batch {" cpp
            members =
              filter (not . Txt.isPrefixOf "//") $
                filter (not . Txt.null) $
                  map Txt.strip $
                    Txt.lines batch
        last members `shouldBe` "size_t n_attention_lanes = 0;"
      it "keeps today's attention program as the helpers-only program" $ do
        let body name = drop 1 . Txt.lines . methodText name
        body "run_attention_worker_helpers_only" cpp
          `shouldBe` body "run_attention_worker" helpersCpp
        let program = methodText "run_attention_worker_helpers_only" cpp
            decls = T.modDecls tron
            guardOf buffer = T.bufferGuardChannel $ T.readDecl buffer decls
            attentionChannels =
              S.fromList
                [ channel
                | T.AttentionStmt operation <- T.mainKernel tron
                , buffer <- [T.attentionQuery operation, T.attentionOutput operation]
                , Just channel <- [guardOf buffer]
                ]
            used =
              S.fromList
                [ name
                | (name, _) <- T.getChannels decls
                , ("q_batch->" <> Txt.pack (show name) <> ",") `Txt.isInfixOf` program
                ]
        used `shouldSatisfy` (not . S.null)
        used `shouldSatisfy` (`S.isSubsetOf` attentionChannels)
      it "dispatches per pass and runs the prologue, then windows in order" $ do
        appearsInOrder
          [ "void run_attention_worker("
          , "if (q_batches[0]->plugin_batch.n_attention_lanes == 0) {"
          , "run_attention_worker_helpers_only(q_batches, worker_ix, n_attn_workers);"
          , "return;"
          , "run_attention_worker_aligned(q_batches, worker_ix, n_attn_workers);"
          ]
          cpp
          `shouldBe` True
        appearsInOrder
          [ "void run_attention_worker_aligned("
          , "TRON_ASSERT(q_batch->n_attention_lanes == n_attn_workers,"
          , "attention_prologue(q_batch, worker_ix, n_attn_workers);"
          , "run_attention_job<"
          , "attention_window_0(q_batch, worker_ix, n_attn_workers);"
          , "run_attention_job<"
          , "attention_window_1(q_batch, worker_ix, n_attn_workers);"
          , "record_attention_time"
          ]
          cpp
          `shouldBe` True
      it "follows main's order in each window, on the lane side of lane channels" $ do
        let window = methodText "attention_window_0" cpp
            laneSync line =
              any
                (`Txt.isInfixOf` line)
                [ ".start_writing(part)"
                , ".finish_writing(part)"
                , ".start_reading(part)"
                , ".finish_reading(part)"
                ]
            steps =
              [ Txt.strip line
              | line <- Txt.lines window
              , laneSync line || "_lane(q_batch, lane, n_lanes" `Txt.isInfixOf` line
              ]
        map (Txt.takeWhile (/= '(')) (filter (Txt.isInfixOf "_lane(") steps)
          `shouldBe` ["kernel_router_0_lane", "moe_blend_0_lane", "kernel_next_0_lane"]
        length (filter laneSync steps) `shouldBe` 10
        window
          `shouldSatisfy` Txt.isInfixOf
            "kernel_router_0_lane(q_batch, lane, n_lanes, false);"
        methodText "attention_prologue" cpp
          `shouldSatisfy` Txt.isInfixOf "kernel_embed_lane(q_batch, lane, n_lanes);"
      it "splits each domain kernel into a helper entry point and a lane method" $ do
        appearsInOrder
          [ "void kernel_router_0("
          , "const size_t n_helpers = (n_workers == 1) ? 1 : n_workers - 1;"
          , "const size_t n_lanes = tron::aligned_lanes("
              <> "q_batch->items.size(), n_workers, app_pool().num_workers());"
          , "kernel_router_0_lane(q_batch, lane, n_lanes, "
              <> "q_batch->items.size() <= n_helpers);"
          , "void kernel_router_0_lane("
          , "if (lane < q_batch->items.size() && touch) {"
          , ".touch();"
          , ".start_reading_at(lane);"
          , "for (size_t task = lane; task < q_batch->items.size(); task += n_lanes) {"
          ]
          cpp
          `shouldBe` True
        methodText "kernel_attn_in_0" cpp
          `shouldSatisfy` Txt.isInfixOf "task += n_actual_workers"
      it "waits for guarded blend weights on either stripe" $ do
        -- The fixtures' blend weights have no guard channel, so add one
        -- produced by a matmul.
        let guardWeights consumer m = do
              weights <- case [w | T.MoeBlendStmt _ w _ _ _ _ _ <- T.mainKernel m] of
                w : _ -> pure w
                [] -> expectationFailure "expected a blend"
              let decls = T.modDecls m
                  info = T.readDecl weights decls
                  channel = "blend_weights_channel"
                  channelInfo =
                    T.ChannelInfo
                      { T.channelScalarType = T.bufferScalarType info
                      , T.channelWidth = T.bufferWidth info
                      , T.channelIterSpace = T.bufferIterSpace info
                      , T.channelProducer = T.MatrixP [T.bufferWidth info] T.Device
                      , T.channelConsumer = consumer
                      , T.channelProvenance = emptyProvenance
                      }
              T.bufferGuardChannel info `shouldBe` Nothing
              pure
                m
                  { T.modDecls =
                      T.redeclare weights info{T.bufferGuardChannel = Just channel} $
                        T.declare channel channelInfo decls
                  }
            waits = Txt.isInfixOf "q_batch->blend_weights_channel.start_reading_at("
        aligned <- guardWeights (T.LaneC QBatchItems) tron
        methodText "moe_blend_0_lane" (renderCpp aligned) `shouldSatisfy` waits
        striped <- guardWeights (T.ParC QBatchItems) helpers
        methodText "moe_blend_0" (renderCpp striped) `shouldSatisfy` waits
      it "includes the lane rule only with aligned lanes" $ do
        cpp `shouldSatisfy` Txt.isInfixOf "#include \"tron/models/kernel_strategy.hpp\""
        mapM_
          ( \other ->
              renderCpp (LoopyTron.process other)
                `shouldSatisfy` ( \c ->
                                    not (Txt.isInfixOf "aligned_lanes" c)
                                      && not (Txt.isInfixOf "n_attention_lanes" c)
                                )
          )
          [L.moeExample, explicitAttentionModule]
    describe "prepares around the MoE router" $ do
      -- See Note [Prepares around the MoE router] in LoopyTron/BufferReuse.hs.
      let hostRouters = LoopyTron.process L.laneDomainExample
          sitesOf channel tron =
            [site | (prepared, site) <- prepareSites tron, prepared == channel]
          isMoeLaunch = \case
            T.MoeMatmulPrepareAndLaunchStmt{} -> True
            _ -> False
      it "prepares a reused routing slot at its router" $
        -- Layer 1's routing reuses layer 0's routing slot. The midpoint rule
        -- would prepare the slot before layer 1's attn_in kernel.
        sitesOf "routing_0_channel" hostRouters
          `shouldBe` ["kernel_attn_in_0", "moe_route 1"]
      it "keeps buffer prepares out of the router window" $ do
        -- Layer 1's QKV input reuses qkv_in_0's buffer. The midpoint rule would
        -- prepare it before layer 0's up launch, inside layer 0's router window.
        sitesOf "qkv_in_0_channel" hostRouters
          `shouldBe` ["kernel_embed", "moe_route 0"]
        [ channel
          | T.MoeRouteStmt{} : rest <- tails (T.mainKernel hostRouters)
          , T.ChannelPrepareStmt channel _ <- takeWhile (not . isMoeLaunch) rest
          ]
          `shouldBe` []
      it "selects host-router prepares only for MatVec kernels" $ do
        let placement = LoopyTron.preparePlacement . L.moduleFunction
        map placement [L.laneDomainExample, L.moeMatVecExample]
          `shouldBe` [BR.HostRouterPrepares, BR.HostRouterPrepares]
        map placement [laneDomainWithDeviceRouters, L.moeExample]
          `shouldBe` [BR.MidpointPrepares, BR.MidpointPrepares]
      it "keeps midpoint prepares with device routers" $ do
        -- laneDomainWithDeviceRouters has router windows, so the two placements
        -- schedule it differently. The placement that LoopyTron selects must
        -- give the midpoint schedule.
        let schedule placement =
              either expectationFailure pure $
                prepareScheduleWith placement laneDomainWithDeviceRouters
            selected =
              LoopyTron.preparePlacement (L.moduleFunction laneDomainWithDeviceRouters)
        midpoint <- schedule BR.MidpointPrepares
        schedule BR.HostRouterPrepares >>= (`shouldNotBe` midpoint)
        schedule selected `shouldReturn` midpoint
        -- So LoopyTron.process prepares the routing slot before each layer's
        -- attention job, not at the router.
        sitesOf "routing_0_channel" (LoopyTron.process laneDomainWithDeviceRouters)
          `shouldBe` ["attention 0", "attention 1"]
      describe "on a synthetic router window" $ do
        -- See routerWindowPrepares: the window is (10, 14].
        let prepares placement entries =
              either expectationFailure pure $
                routerWindowPrepares placement entries
            buffer = L.Array RealScalar (Just QBatchItems) (Static 8)
            reusePrepare placement previous next =
              (M.! "b")
                <$> prepares placement [("a", buffer, previous), ("b", buffer, next)]
        it "moves a buffer prepare in the window to the router" $ do
          -- a is last read at 3 and b is first written at 20, so the midpoint
          -- is 12.
          reusePrepare BR.MidpointPrepares (0, 3) (20, 21) `shouldReturn` [LA.Time 12]
          reusePrepare BR.HostRouterPrepares (0, 3) (20, 21) `shouldReturn` [LA.Time 10]
        it "keeps a buffer prepare if the previous read is in the window" $
          -- The midpoint 14 is in the window, but a is last read at 11, after
          -- the router.
          reusePrepare BR.HostRouterPrepares (0, 11) (17, 18) `shouldReturn` [LA.Time 14]
        it "keeps buffer prepares outside the window" $ do
          -- The midpoints fall before the router (5), at it (10) and after the
          -- window (17).
          reusePrepare BR.HostRouterPrepares (0, 2) (8, 9) `shouldReturn` [LA.Time 5]
          reusePrepare BR.HostRouterPrepares (0, 4) (15, 16) `shouldReturn` [LA.Time 10]
          reusePrepare BR.HostRouterPrepares (0, 3) (30, 31) `shouldReturn` [LA.Time 17]
        it "prepares a reused routing slot at its router" $ do
          -- routing reuses r0's slot, and the router at 10 writes it. r1 reuses
          -- the slot at 20, where no router writes it.
          let routings =
                [ ("r0", L.type_ routing, (2, 4))
                , ("r1", L.type_ routing, (20, 22))
                ]
          midpoint <- prepares BR.MidpointPrepares routings
          host <- prepares BR.HostRouterPrepares routings
          map (midpoint M.!) ["routing", "r1"] `shouldBe` [[LA.Time 7], [LA.Time 17]]
          map (host M.!) ["routing", "r1"] `shouldBe` [[LA.Time 10], [LA.Time 17]]
