# inter_bridge

跨链买 Token 项目的调研与设计仓库。

## 文档

| 文档 | 内容 |
|---|---|
| [docs/pump-bridge-vs-relay.md](docs/pump-bridge-vs-relay.md) | Pump.fun 自研 Pump Bridge 与 Relay（Solver 网络）方案对比：机制、系统架构图、资金流转图（含各项费用，已用链上数据对账）、Pump 弃用 Relay 的原因，以及我们项目的架构设计和落地路线 |

> 文档里的 12 张图是 SVG（`docs/diagrams/*.svg`），任何 Markdown 预览器都能直接显示；`docs/diagrams/png/` 里有 2 倍清晰度的 PNG，方便发到飞书 / 微信。
>
> **改图**：编辑 `docs/diagrams/gen.py` 里对应的 `fig_xxx()` 函数（文字、金额、坐标），然后运行 `python3 docs/diagrams/gen.py` 重新生成。样式统一在 `docs/diagrams/svgkit.py`。导出 PNG 需要 `rsvg-convert`（`brew install librsvg`）。

## 我们项目的需求（已确认）

- **充值**：支持多条链充值（Solana + 各 EVM 链）。
- **插件钱包**：支持，但只能买本链代币（直接走本链 DEX 聚合器）。
- **跨链买币**：只给第三方登录钱包用，私钥由服务器托管，不能导出。

## 当前结论（摘要）

- **Relay**：通用、去信任、零资本，但链路长、费用叠加、meme 场景下失败率约 11%。
- **Pump Bridge**：自营库存式桥，两条链各一笔交易，约 1~2 s、失败率 0.9%。实测 Pump 是混合路由：USDC 买走自营，SOL 买仍走 Relay，卖出一律自营。收费规则：卖出 = 0.45% + gas 实报实销（链上已确认），买入 = 0.45% + 约 $0.05（推测）。
- **我们的方案**：自营库存桥处理对延迟敏感的跨链买卖，Relay / CCTP 处理长尾链、充值提现和再平衡；托管钱包 + EIP-7702 代付 gas；分阶段落地。

## 待办

- [ ] 用 10 / 100 USDC 测试，拆出 Pump 买入的固定费
- [x] 确认 Pump 用 SOL 买时的资金路径（走 Relay，见文档 §3.7）
- [ ] 验证 SOL 买入的路由规则（金额 / 链 / A/B 分流）
- [ ] 确认启动资金和团队配置，决定从哪个阶段开始
- [ ] 托管密钥服务选型（Turnkey / Privy Server Wallet / Fireblocks / 自建）
