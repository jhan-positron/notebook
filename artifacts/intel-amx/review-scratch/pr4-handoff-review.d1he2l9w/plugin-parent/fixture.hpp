outer_state.template save_v<G>(q_batch->outer_batch, v);
outer_state.template save_k<G>(q_batch->outer_batch, correct_k, 0, n_workers);
outer_state.template save_k<G>(q_batch->outer_batch, correct_k, worker_ix, n_workers);
