Is it possible we can run runtron with certain parameters so that:
1. Each run generates identical token sequence
2. At the end of each layer, the candidate logits are identical compared to same token at the same layer
3. At the end of each layer, the picked logit is identical compared to the same token at the same layer

I think we can achieve the above if:
- Use dense model
- Use same seed
- Set temperature to 0

The motivation: we need to facilitate the debug of AMX implementation. One solution is, we run runtron twice with the parameter set as discussed above and they are supposed to generate same token sequence and internal data like logits. By comparing these data, we will be able to quickly identify bugs.

Let's do a brainstorm of the above:
1. Is the idea sound? If yes, please fill out what it missed
2. If not, what's your suggestion to fulfull the motivation?
3. And what about MoE models such as gpt-oss? How can we achieve the same motivation?

Please generate discuss-definitive-decode.html to from-claude/.
