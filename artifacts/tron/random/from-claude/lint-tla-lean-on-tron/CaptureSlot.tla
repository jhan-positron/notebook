---------------------------- MODULE CaptureSlot ----------------------------
(* Model of tron::trace_detail::capture_controller                         *)
(* (src/pos/trace_capture.cpp, tron commit 7eddde7895, 2026-11-21).        *)
(*                                                                         *)
(* Each controller method holds the mutex for its whole body, so one       *)
(* method call is one step (one "action") here.                            *)
(*                                                                         *)
(* NOT run through TLC in the session that wrote it: Java was not          *)
(* installed. capture_slot_check.py is the same model in Python and was    *)
(* run. Check this file with:                                              *)
(*   java -cp tla2tools.jar tlc2.TLC -config CaptureSlot.cfg CaptureSlot   *)
EXTENDS Naturals

CONSTANT MaxStarts      \* how many start commands the model tries

VARIABLES
  slot,     \* "empty", or active_->state: accepted/waiting/recording/stopping
  slotId,   \* active_->id as a number, 0 when the slot is empty
  stopReq,  \* active_->stop_requested
  sigusr1,  \* sigusr1_active_
  worker,   \* where the worker thread is: idle/setup/aborting/recording/stopping
  job,      \* id of the record take_start() gave the worker, 0 when idle
  nextId    \* next_sequence_

vars == <<slot, slotId, stopReq, sigusr1, worker, job, nextId>>

Init ==
  /\ slot = "empty"
  /\ slotId = 0
  /\ stopReq = FALSE
  /\ sigusr1 = FALSE
  /\ worker = "idle"
  /\ job = 0
  /\ nextId = 1

\* finish_locked(): the record leaves the slot.
Free ==
  /\ slot' = "empty"
  /\ slotId' = 0
  /\ stopReq' = FALSE

----------------------------------------------------------------------------
\* FUSE request thread: command()

Start ==
  /\ nextId <= MaxStarts
  /\ slot = "empty"              \* else the reply is "busy"
  /\ ~sigusr1                    \* else the reply is "busy"
  /\ slot' = "accepted"
  /\ slotId' = nextId
  /\ stopReq' = FALSE
  /\ nextId' = nextId + 1
  /\ UNCHANGED <<sigusr1, worker, job>>

StopBeforeWorker ==              \* "The worker never saw it: no window."
  /\ slot = "accepted"
  /\ Free
  /\ UNCHANGED <<sigusr1, worker, job, nextId>>

StopRequest ==
  /\ slot \in {"waiting", "recording", "stopping"}
  /\ ~stopReq                    \* a repeated stop changes nothing
  /\ stopReq' = TRUE
  /\ UNCHANGED <<slot, slotId, sigusr1, worker, job, nextId>>

----------------------------------------------------------------------------
\* Capture worker thread

TakeStart ==                     \* take_start(): accepted -> waiting
  /\ worker = "idle"
  /\ slot = "accepted"
  /\ slot' = "waiting"           \* seeded bug 1: write "accepted" here
  /\ worker' = "setup"
  /\ job' = slotId
  /\ UNCHANGED <<slotId, stopReq, sigusr1, nextId>>

\* The next four actions start with TRON_ASSERT(active_) in the C++ code.
\* With an empty slot the process aborts, so the guard is slot # "empty".

SetupFails ==                    \* file or session setup failed: finish(failed)
  /\ worker = "setup"
  /\ slot # "empty"
  /\ Free
  /\ worker' = "idle"
  /\ job' = 0
  /\ UNCHANGED <<sigusr1, nextId>>

BeginRecording ==                \* begin_recording()
  /\ worker = "setup"
  /\ slot # "empty"
  /\ IF stopReq
       THEN (worker' = "aborting" /\ slot' = slot)
       ELSE (worker' = "recording" /\ slot' = "recording")
  /\ UNCHANGED <<slotId, stopReq, sigusr1, job, nextId>>

SetStopping ==                   \* set_stopping(): stop request or deadline
  /\ worker = "recording"
  /\ slot # "empty"
  /\ slot' = "stopping"
  /\ worker' = "stopping"
  /\ UNCHANGED <<slotId, stopReq, sigusr1, job, nextId>>

Finish ==                        \* finish(): the worker ends the capture
  /\ worker \in {"aborting", "stopping"}
  /\ slot # "empty"
  /\ Free
  /\ worker' = "idle"
  /\ job' = 0
  /\ UNCHANGED <<sigusr1, nextId>>

----------------------------------------------------------------------------
\* SIGUSR1 thread

SigBegin ==                      \* begin_sigusr1() returns true
  /\ ~sigusr1
  /\ slot = "empty"
  /\ sigusr1' = TRUE
  /\ UNCHANGED <<slot, slotId, stopReq, worker, job, nextId>>

SigEnd ==                        \* end_sigusr1()
  /\ sigusr1
  /\ sigusr1' = FALSE
  /\ UNCHANGED <<slot, slotId, stopReq, worker, job, nextId>>

----------------------------------------------------------------------------
Next ==
  \/ Start \/ StopBeforeWorker \/ StopRequest
  \/ TakeStart \/ SetupFails \/ BeginRecording \/ SetStopping \/ Finish
  \/ SigBegin \/ SigEnd

Spec == Init /\ [][Next]_vars

----------------------------------------------------------------------------
\* The rules. TLC tests each one in every reachable state.

\* A SIGUSR1 capture never runs while a FUSE capture holds the slot or the
\* worker runs one.
OneCapture == ~(sigusr1 /\ (slot # "empty" \/ worker # "idle"))

\* While the worker runs a capture, the slot is not empty. This is the
\* TRON_ASSERT(active_) in begin_recording, set_stopping and finish_locked.
AssertActive == (worker # "idle") => (slot # "empty")

\* The capture in the slot is the one the worker runs.
OwnJob == (worker # "idle" /\ slot # "empty") => (slotId = job)
=============================================================================
