**Observations:**

*Wall channel (channel 3).* The border cells' channel-3 weights all share one small pattern, roughly (0.0, +0.2, −0.1, −0.2, +0.1, −0.2, −0.15, +0.15 …). Examples are input 3 (row 0, col 0) "−0.080 0.255 −0.015 −0.141", input 403 "0.065 0.231 −0.099 −0.115" and input 498 "0.118 0.316 −0.145 −0.049". That is what an always-on input looks like: it acts like a bias. Inner channel-3 weights are near zero (about ±0.1), so there are no inner obstacles.

*Agent channel (channel 0).* It is essentially untrained (about ±0.1) in rows 1–7. It is large only in row 8, the bottom playable row:
- (8,8): 3.855, 3.730
- (8,7): −2.107, 1.169
- (8,2): −1.930, 2.794
- (8,4): 1.605, 1.444

So the agent lives only on the bottom row.

*Moving-object channel (channel 1).* It carries huge weights (3 to 7 in magnitude) at almost every cell in rows 1–7:
- (1,3): 3.194, 2.708, −4.791
- (2,2): 3.408, −6.356
- (3,7): 5.458, −5.282

It is near zero in row 8, for example (8,7) "−0.052 −0.063" and (8,8) "−0.047 −0.073". So a moving object travels all over the upper field and never enters the agent's row.

*Previous-frame channel (channel 4).* It is equally large in rows 1–7, with the same sign pattern as channel 1. For example, unit 7 is strongly negative in both: (2,3) ch1 −5.493 and ch4 −5.154. This gives the network the object's previous position, i.e. its direction of travel. In row 8, channel 4 is moderate, reflecting the agent's previous position.

*Reward channel (channel 2).* It is sizeable only in rows 1–3:
- (3,1): −4.811 (unit 0), −3.236 (unit 20)
- (3,7): −4.640, −2.930
- (3,8): −2.944
- (3,3): 2.365
- (1,5): 2.148

It is near zero from row 4 down, for example (4,1) "−0.017 −0.050", (6,6) 0.048 and (7,8) −0.059. So the reward targets form a static block in the top three rows. Input 92, (1,8) channel 2, even has the bias-like wall pattern. That fits a target that is almost always present, such as a rarely-hit corner brick.

*Output layer.* Columns 0, 1 and 2 (no-op, up, down) are nearly identical in every row of W3:
- unit 1: 1.502 /