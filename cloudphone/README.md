# 云手机（红手指）上跑脚本

怎么用：[USER_GUIDE.md](USER_GUIDE.md)（日常使用、更新、换实例、常见问题）。下面是技术说明。

脚本在云手机**内部**运行：`/data/local/tmp/ip` 里用 proot 跑一个 Alpine Linux（不需要 root，不装任何 App），
里面的 Python 通过手机自己的 adb（`127.0.0.1:5555`）截图和点击，截图 ~0.3 秒。
后台服务 `supervisor.py`（只监听手机本机 `127.0.0.1:8765`）一次跑一个脚本；浮窗 App「星球脚本」可以选脚本、开始、停止、更新。
Mac 只在部署和调试时通过 Tailscale + adb 连手机，命令都在 `cloudphone/cp.sh`。

## 换新实例
1. 手机上：设置 → 关于手机 → 连点版本号 → 系统 → 开发者选项 → 打开 **USB 调试**。
2. 装 Tailscale 并用和 Mac 同一个账号登录，把手机的 100.x 地址写进 `cloudphone/.serial`（例如 `100.104.162.101:5555`）。
3. Mac 上：`cloudphone/cp.sh all`（装环境、从 GitHub 拉代码、装浮窗、启动服务）。
4. 手机上打开游戏登录（同一账号只能在一台设备在线）。

## 日常
- 浮窗：点小圆点 → 选脚本 → 开始。小圆点默认在右上角，随时能拖能点，运行时变小、半透明的绿色「运行」。脚本每次点击前重新读浮窗窗口（`dumpsys window`，含 adb 往返约 0.1 秒；不缓存，免得点到刚打开的面板上）：要点在浮窗上，就在同一条 shell 里先广播 `com.ip.panel.HIDE`（隐身 3 秒、点击穿透，每次点击续期）；面板开着挡住要点的地方，先等最多 12 秒。脚本每分钟广播 `com.ip.panel.HELLO`（浮窗记 3 分钟）；运行中的脚本没报到（旧代码），小圆点就保持点击穿透。右上角查过：要塞脚本读的模板都不在那里；资源派遣扫描整张地图上的资源，右上角也会有，移植它时要在扫描的截图前让小圆点隐身。
- 更新：代码推到 GitHub 后，浮窗点「更新」（拉最新代码、更新脚本列表等手机端文件，重启正在跑的脚本；服务本身改了也会重启服务）。
- 脚本出错退出会在 60 秒后自动重启（每小时最多 5 次）；正常结束的和试跑（--dry）的不重启。
- 停止（停止、更新、`cp.sh restart`）给脚本发 SIGTERM：fortress_fight 在下一个安全点退出（两轮之间、换装或出击开始前；换装做到一半就做完或放弃并把装备装回去），最多等 240 秒，超时才 SIGKILL；脚本退出后，它留下的子进程（比如没做完的 adb 点击）也一起结束。万一还是被硬杀在换装中间：换装模式记着上一任装备主人（`fortress_gear.json`），下次开头找不到带装备的船，就在它身上点一键配队把散着的装备收回来。这类状态文件（`cp.sh` 里的 `STATE_FILES`）在重新克隆代码时会保留。
- 手机重启后：点「星球脚本」图标 → 面板里「启动服务」，会接着跑重启前在跑的脚本。
- 脚本列表在 `cloudphone/phone/scripts.json`：平铺的列表 `[{"group", "id", "name", "args", "restart"?}]`，`group` 是类别（面板一次显示一类），`id` 全文件唯一。保持平铺是为了新旧版本的服务和浮窗都能读。服务会自动加上 `--adb 127.0.0.1:5555 --delay 0`，目前只有 fortress_fight.py 支持 `--adb`。
- 更新：一次只跑一个，`/status` 的 `updating` 说明正在做什么（面板显示「更新中」）；分三步：拉提交；把改动的文件内容下载到临时目录（手机上的仓库是按需下载的，这一步才是大头）；本地切换代码。前两步速度低于 1 KB/s 满一分钟就放弃这一次，网络问题会再试一次；下载被打断不会留下换了一半的代码。`cp.sh code`/`setup` 把电脑上的代码放到手机时，在 `/ip/local_code` 记下这份代码的时间；GitHub 上最新提交比它旧（还没推送）就不更新，`cp.sh update --force` 除外。服务拉代码后，自己的代码变了就重启自己（比较的是正在运行的代码；新的 supervisor.py 先在子进程里试加载，加载不了（语法错误、导入失败）就不重启，旧服务照常运行，只把脚本重启到新代码），`cloudphone/app/panel.apk` 变了就通过本机 adb 装新浮窗（`/ip/panel.apk.sha` 记着装的是哪个，`cp.sh app` 也写它）。`cp.sh code`/`setup`/`code --github` 推来新的 supervisor.py 时，正在运行的服务会被安全重启；`cp.sh restart` 运行手机上的 `restart.sh`：找到正在运行的服务（`supervisor.pid` 丢了就按命令行找），每 10 秒重发一次停止信号，旧服务退出后启动新的；10 分钟后旧服务还没退出，就转到手机后台继续等（最多一小时），命令以退出码 3 结束。

## cp.sh 命令
| 命令 | 作用 |
|---|---|
| `all` | 新手机：setup + code --github + app + up |
| `setup` | 装 proot、Alpine、Python/opencv/tesseract/adb/git（装过的跳过） |
| `code [--github]` | 把本地代码推到手机（测试没推送的改动）；`--github` 让手机自己拉 origin/main |
| `app` | 编译（源码变了才编）并安装浮窗 |
| `up` / `restart` | 启动服务和浮窗 / 重启服务（脚本会接着跑） |
| `scripts` `status` `log [N]` `start ID` `stop` `update` | 控制服务 |
| `try 参数...` | 测试：先停掉服务正在跑的脚本，在前台跑一次 `python3 -u 参数 --adb 127.0.0.1:5555 --delay 0`，再把原来的脚本启动回来 |
| `peek [比例]` | 手机屏幕 JPEG（手机上压缩，~1 秒） |
| `pull 路径` | 手机上的图片（例如 debug 截图）转 JPEG 拉回 |
| `sh 命令` | 在手机的 Alpine 里执行（当前目录 /ip） |

## 文件
- `phone/`：放到手机 `/data/local/tmp/ip` 的文件：`setup.sh`（装环境）、`run.sh`（进 Alpine）、`start.sh`（启动服务）、`restart.sh`（等旧服务安全停下再启动新的）、`supervisor.py`、`scripts.json`、`peek.py`/`jpg.py`（调试截图）。
- `app/`：浮窗 App（Java，无 Gradle，`build.sh` 编译；第一次会下载约 150 MB 的安卓编译工具到 `app/.sdk`）。`panel.apk` 一起提交，换电脑不用重新编。
- 手机上：`/data/local/tmp/ip/app`（代码，GitHub 稀疏检出）、`logs/`（每个脚本的日志、服务日志）、`state.json`（重启后接着跑哪个脚本）。

## 已知情况
- 红手指禁止安装 Termux；UserLAnd 2021 版拉不到应用列表。现在的方案只用 adb shell 用户 + proot。
- 从 Mac 远程截原图很慢（~13 秒/张，走 Tailscale 中转），调试一律用 `peek` / `pull`。
- 模板用 Mac 那套（`pics/mac/zone`），截图按宽度缩放到 Mac 参考尺寸（993.8），720p 上匹配分数 ≥ 0.98，不用重截。
