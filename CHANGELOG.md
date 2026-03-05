

### Bug Fixes

- Remove unused init_child variable in transaction detail ([983e402](https://github.com/Ahacad/simledge/commit/983e402bcc6087fee84dee6e11e0e8260dc2ab08))

### Features

- Add force apply levels and widen CC payment date window ([520e9ad](https://github.com/Ahacad/simledge/commit/520e9add1d9c791c4f7b571cb439a76268654f11))

### Bug Fixes

- Fix Enter key on transactions table ([1c33931](https://github.com/Ahacad/simledge/commit/1c339319265712af273b401c5af101aecc30a153))
- Set DataTable cursor_type to row for Enter to work ([1f1151d](https://github.com/Ahacad/simledge/commit/1f1151d1bc00dfada9487550631f3f158b811cbf))
- Correct hint text — Right arrow accepts suggestion, not Tab ([0df011d](https://github.com/Ahacad/simledge/commit/0df011db5862dcaa134fc62504ec1a333a7ac7ce))
- Use Select.NULL instead of Select.BLANK for no-selection ([d179536](https://github.com/Ahacad/simledge/commit/d1795365984844e54f7e1f9caa828ef9a4165b76))
- Category colors, chart exact numbers, trends arrow direction, rules flex columns, budget TOML init ([a87876a](https://github.com/Ahacad/simledge/commit/a87876af7e3fcb74446ae4279fb43f75258b32d7))
- Exclude Transfer categories from spending totals ([5d15405](https://github.com/Ahacad/simledge/commit/5d15405b029d3b024be45b05c595cd92b99d21b8))
- Detect CC payment transfers, exclude from spending totals ([c00ea1c](https://github.com/Ahacad/simledge/commit/c00ea1c2c6b4d2a35ed24b4f791945d3d6e27d5d))
- Wire CC payment detection into force-apply and new `rule apply` CLI ([ee3a4b0](https://github.com/Ahacad/simledge/commit/ee3a4b0573f8549f8a635fa91ea15698c671f2e4))
- Drop description gate from CC payment detection ([b672cbf](https://github.com/Ahacad/simledge/commit/b672cbfa6902b2c2f8c56641024694581aeddb30))
- Handle CC accounts with NULL type via description fallback ([e97df87](https://github.com/Ahacad/simledge/commit/e97df875640ed0421099b4da54c6b2833a08934b))
- Use Select.NULL instead of Select.BLANK for type selector ([828b158](https://github.com/Ahacad/simledge/commit/828b158aaa26acb236f5805f07337e97cd7eb471))
- Defer data load to after first render frame ([3501cc8](https://github.com/Ahacad/simledge/commit/3501cc82c5eb4830c7a1bd228fc15bb832dff70d))

### Features

- Add RULES_PATH constant for category rules file ([8f80160](https://github.com/Ahacad/simledge/commit/8f801604e7b85b11dac6527774da670bcd084ca5))
- Rewrite rule engine to use TOML file as source of truth ([aeafa13](https://github.com/Ahacad/simledge/commit/aeafa13e41e74de3c78772e15e4c009da920f3e6))
- Auto-apply category rules from TOML after sync ([cebe959](https://github.com/Ahacad/simledge/commit/cebe959ad07d90680573ab4f8a38b8023bc166e3))
- Rewrite rule commands to use TOML file ([f4d0654](https://github.com/Ahacad/simledge/commit/f4d0654cb2e33f17b99781ec5f405a77778300af))
- Rewrite Rules screen to use TOML file ([e5f4a84](https://github.com/Ahacad/simledge/commit/e5f4a846bf07d7317bd48bf33f0bad5321e45715))
- TOML-based category rules with preset defaults ([f70c483](https://github.com/Ahacad/simledge/commit/f70c483f3ddc20b532e0a798b06fc9263c1f30ca))
- Rewrite Accounts screen with DataTable and editable display names ([9c6a05f](https://github.com/Ahacad/simledge/commit/9c6a05f36b3b7d0d3ec76486cb4193dde1619175))
- Add value labels on chart bars and data tables below charts ([3e5f84d](https://github.com/Ahacad/simledge/commit/3e5f84d94a18f7c84f6498e7ee354800bb1e59e2))
- Use display_name for accounts in transactions and filter modal ([36ed3f0](https://github.com/Ahacad/simledge/commit/36ed3f0240ccc4d2ce360f1ea79b84c976651bae))
- Add spending by category panel with subcategory breakdown ([caa9cb3](https://github.com/Ahacad/simledge/commit/caa9cb3667181326a58a7fa7c77252a9ca127416))
- Add category autocomplete and rule-based prefill ([961138d](https://github.com/Ahacad/simledge/commit/961138df51de4e6c8b9b7025db89b4aaaacef593))
- Replace category input with Select dropdown + custom option ([85e0c1b](https://github.com/Ahacad/simledge/commit/85e0c1b3bcb88058c65c3ebb17180e474487957b))
- Two-stage category selection — parent then subcategory ([6c147a9](https://github.com/Ahacad/simledge/commit/6c147a9847098fed3d88a95405861dba633e572e))
- Promote Groceries to top-level category, add Housing:Rent, add force-apply action ([627976b](https://github.com/Ahacad/simledge/commit/627976b03d34a4e3e4e57dba2135414e592c87d9))
- Enrich overview, fix YoY arrows, color categories, cap rule widths, migrate budgets to TOML ([0b95841](https://github.com/Ahacad/simledge/commit/0b95841485478abf5cdee1158b2d45ceb614f3a9))
- Detect CC payment transfer pairs ([9034c2c](https://github.com/Ahacad/simledge/commit/9034c2cd2072ff2a0a5e44158bb2cea64e32f3a5))
- Add account type editing with 't' key ([b2358b7](https://github.com/Ahacad/simledge/commit/b2358b740357df3e0904c71d09872745865e9491))
- Add Loan account type option ([09df571](https://github.com/Ahacad/simledge/commit/09df5713baf8a4f8a99515c6507c0ac3025dcc94))

### Bug Fixes

- Extract f-string backslash expressions for Python 3.11 compat ([4432d15](https://github.com/Ahacad/simledge/commit/4432d158ddad0abf2be56917e624b6b933238258))
- Fix input focus trap, add navbar, add escape to leave search ([a85d958](https://github.com/Ahacad/simledge/commit/a85d95899caaf2047dd1568b1d603b5851f6cd1a))
- Fix plotext chart rendering, add help screen, disable command palette ([dd88690](https://github.com/Ahacad/simledge/commit/dd88690ffcf07e558b306c77aa14dab9bcda9337))
- Fix SimpleFIN API endpoint, pending dates, and add data safety ([57e91fd](https://github.com/Ahacad/simledge/commit/57e91fd72a02df680832edfcfe6b762f6a80b465))
- Exclude credit card accounts from income and negative alerts ([dedb31b](https://github.com/Ahacad/simledge/commit/dedb31b8183f4c0b27354b1ecd5f8f450ce34ac5))
- Re-render plotext charts on terminal resize ([71095c3](https://github.com/Ahacad/simledge/commit/71095c353448a015bb222f53b0d2971fa334b98f))
- Goals cursor selection, watchlist DB leak, help text, cashflow logging ([45b7c7a](https://github.com/Ahacad/simledge/commit/45b7c7a3904e73ead4505b40d7a22efa8a0c8650))

### Features

- Scaffold project with CLI entry point and packaging ([2edd148](https://github.com/Ahacad/simledge/commit/2edd1482a0a839ab57f958eebede6ef5ac4970aa))
- Add platform paths, config constants, and logging ([5cab7ef](https://github.com/Ahacad/simledge/commit/5cab7efb99d2b94d5ab34e357ccad36312663966))
- Add SQLite schema with upsert helpers and balance snapshots ([6f65c03](https://github.com/Ahacad/simledge/commit/6f65c0331a792e9bc89aba97f5897577e91a9b66))
- Add SimpleFIN client with response parsing and DB sync ([561e869](https://github.com/Ahacad/simledge/commit/561e8699ad06c9bc152df4fead69eaf44c4b574b))
- Add regex/keyword rule engine for transaction categories ([765dd5d](https://github.com/Ahacad/simledge/commit/765dd5d47371c11d0f186fd590d302496600c82b))
- Add spending, trends, net worth, and account summary queries ([e1cd07d](https://github.com/Ahacad/simledge/commit/e1cd07d8e02fc70af3ff9985396eec6f27f5e454))
- Add markdown, CSV, and JSON export for Claude Code analysis ([282171a](https://github.com/Ahacad/simledge/commit/282171a6d3f76418d442f3c0bde94a596d8a7237))
- Wire all subcommands to sync, export, rule, status, setup ([9970080](https://github.com/Ahacad/simledge/commit/9970080761d996e193d4d068bc452d00717e42ad))
- Add app shell with 5 screens and keyboard navigation ([dc469fe](https://github.com/Ahacad/simledge/commit/dc469fe345af2032df44eeca082ffe84adc960e3))
- Implement overview screen with summary, category bars, and recent transactions ([7924cf8](https://github.com/Ahacad/simledge/commit/7924cf84290e21001c85476e0d9774cd02563205))
- Implement transactions screen with search and filtering ([e6544cf](https://github.com/Ahacad/simledge/commit/e6544cf1a3780e655c7580f997b4c785244b27fd))
- Implement accounts screen with balance summary by institution ([cab42ec](https://github.com/Ahacad/simledge/commit/cab42ec21d1ad2b6cf578a489a79dbc82480ef34))
- Implement trends screen with spending chart and category comparison ([133cd93](https://github.com/Ahacad/simledge/commit/133cd934dd6adb7ad4affa2615c57a038a7beee2))
- Implement net worth screen with history chart ([6fcd72a](https://github.com/Ahacad/simledge/commit/6fcd72a6d057b9505281407d7043261e1240212e))
- SimpLedge v0.1.0 — personal finance TUI ([e10c1c7](https://github.com/Ahacad/simledge/commit/e10c1c7de54f916dc38b051f9b189e946266b3b4))
- Add sync from TUI via 's' keybinding ([e3b2f6e](https://github.com/Ahacad/simledge/commit/e3b2f6ec82d08a478e46e8c465b7754d78ab9ce2))
- Add rules management screen ([9e1e01a](https://github.com/Ahacad/simledge/commit/9e1e01af866bced67edbb76276aed3a19f02fcdc))
- Add transaction detail modal with category/notes editing ([7021353](https://github.com/Ahacad/simledge/commit/7021353c4e53f4f7f2c30294876370875e89361a))
- Add recurring detection and Bills screen ([eb7cdc2](https://github.com/Ahacad/simledge/commit/eb7cdc2eccd73adcfd4dedca3c7d622627aa6d54))
- Add date range navigation on all screens ([8afdd65](https://github.com/Ahacad/simledge/commit/8afdd653eb062860897db34583b4abb63da7b97d))
- Add account filtering across all screens ([f20893d](https://github.com/Ahacad/simledge/commit/f20893d29c2d9964b4b3c087634233cd2678baac))
- Add advanced filter modal on transactions screen ([a8da092](https://github.com/Ahacad/simledge/commit/a8da09294ff598563f2e4d556953b4b41630c068))
- Add Parent:Child category hierarchy support ([6a1e1a1](https://github.com/Ahacad/simledge/commit/6a1e1a1389c324257e5e0b614b3287cc607cb0eb))
- Add income breakdown and trend analysis ([e12fe84](https://github.com/Ahacad/simledge/commit/e12fe847ed748cc3bc41dd263b8fbb43d61cbf08))
- Add transaction tagging with filter support ([7016c71](https://github.com/Ahacad/simledge/commit/7016c719c4a6c807d6a4b8458dbc87d97a0015c4))
- Add spending plan with budget vs actual tracking ([0026566](https://github.com/Ahacad/simledge/commit/0026566baba80220250c73274c1d497340ce525f))
- Add projected cash flow using recurring transactions ([6c24d9a](https://github.com/Ahacad/simledge/commit/6c24d9ab49e1a729f52e27b6ad8b10c6c7fc380f))
- Add year-over-year spending and income comparison ([aa3cb73](https://github.com/Ahacad/simledge/commit/aa3cb73592454d426cf2621e7888529788439bf1))
- Add spending watchlists with filter criteria and targets ([1424167](https://github.com/Ahacad/simledge/commit/1424167a0ce1861a35f897fb1d0b5d300bf0ae7a))
- Add bill calendar view with paid/upcoming/overdue status ([e8084be](https://github.com/Ahacad/simledge/commit/e8084be1e8b80765474524811c72a8c3f6fdc46a))
- Add calendar panel styling for grid and details views ([28d42c6](https://github.com/Ahacad/simledge/commit/28d42c662ada5c10c88ebc4c765b97b5668ca141))
- Auto-sync on TUI launch when stale > 24h ([c93bed5](https://github.com/Ahacad/simledge/commit/c93bed5631e1906bcf6c6db766982e5742c5b3e2))
- Replace sparklines with plotext charts ([8244e91](https://github.com/Ahacad/simledge/commit/8244e91643e369ebe0300282febd3e6fa59b241b))
- Sync retry with actionable errors, input validation ([b91b560](https://github.com/Ahacad/simledge/commit/b91b560f3e91973f13078de2c43184fdd97f7f98))
- Add privacy mode toggle (p key) to mask amounts ([4e1d287](https://github.com/Ahacad/simledge/commit/4e1d28790d3f3cce96be5336ebb7dd4b0c829859))

### Refactor

- Replace placeholder screens with real implementations ([c4527e1](https://github.com/Ahacad/simledge/commit/c4527e1f121f6df6217e0865ffe8a86c24c36319))
