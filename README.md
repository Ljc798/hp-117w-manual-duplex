## iPhone 手机控制（新增）

从原来的 PDF → HP 117w Manual Duplex 入口发送文件，Mac 会打开控制网页。iPhone 和 Mac 连接同一个 Wi-Fi，用相机扫描网页上的二维码。第一次连接后，在 Safari 选择“分享 → 添加到主屏幕”。链接和控制口令固定，以后直接点击主屏幕图标，不需要每次扫码；打开着的页面会自动跟随当前任务更新。正面打印、回纸后继续、备注和完成确认都可以在手机操作。也可以直接在 Mac 网页操作。

- Mac 必须保持开机；任务期间脚本通过 caffeinate 阻止空闲睡眠，合盖仍可能休眠。
- 若 macOS 提示本地网络访问，请允许；手机连不上时检查“系统设置 → 隐私与安全性 → 本地网络”及当前 VPN 的局域网设置。
- 链接含随机控制口令，只分享给需要操作打印的人。网页仅监听本机回环与 en0/en1 局域网地址，端口 8717，不需公网部署。
- 安装会保留已安装版本的打印机配置，并备份旧应用。需要 Python 3，安装时记录解释器路径。
- 不会自动打印：必须点击开始正面；背面还需点击确认回纸。重复点击、旧页面提交不会重复执行。
- 取消只停止后续步骤，已提交的打印任务由 macOS 打印中心管理。
- 控制服务按需启动，链接可收藏；网络地址变化后退出旧服务再重新打开工作流。

# HP 117w Manual Duplex

[简体中文](#简体中文) | [English](#english)

## 简体中文

一个 macOS PDF 服务，用于没有自动双面器的打印机。它将 PDF 拆成正反两次单面打印，并在两次打印之间提示重新放纸。

### 功能

- 从 macOS 打印窗口左下角的 **PDF → HP 117w Manual Duplex** 启动。
- 先打印一面，等待纸张打印完成后提示重新放纸，再打印另一面。
- 打印完成后可填写备注，也可以跳过。
- 所有记录追加到 `~/Documents/HP 117w Manual Duplex Print Log.xlsx` 的 `Print Log` 工作表。
- 打印完成后询问是否打开 Excel 日志；默认不打开。
- 记录打印时间、传入 PDF 名称、传入 PDF 页数、纸张数、打印机、状态和备注。
- 不记录“From Page / To Page”。打印窗口选定的范围由 macOS 先应用到交给 PDF 服务的 PDF；此工具只记录收到的 PDF 页数。

### 安装

1. 安装并在 macOS 中添加打印机，先确认普通打印可用。
2. 用文本编辑器打开 `main.applescript`，将 `queueName` 改为本机 CUPS 队列名称，将 `printerLabel` 改为显示名称。可运行 `lpstat -p` 查看队列名称。
3. 确保 `~/Documents/HP 117w Manual Duplex Print Log.xlsx` 已存在，包含名为 `Print Log` 的工作表，A1:G1 按顺序写入：`Printed at`, `PDF`, `Pages`, `Sheets`, `Printer`, `Status`, `Notes`。
4. 运行：

   ```sh
   ./install.sh
   ```

5. 在 macOS 打印窗口左下角的 PDF 菜单中选择 **Edit Menu…**，确认启用 **HP 117w Manual Duplex**。如果菜单没更新，重新打开使用中的应用。

### 兼容性

此仓库按 HP Laser MFP 117w 的队列和手动回纸方式配置。代码使用 macOS PDF Services、AppleScript、PDFKit 和 CUPS `lp`。其他打印机即使能接受 CUPS 单面打印，也需要设置正确队列，并校准出纸方向和回纸方式；未经逐台测试，不承诺兼容。当前没有经过验证的其他型号名单。

### 限制

- A4、黑白、单份、每页一面为固定设置。
- 页数是 PDF 服务交来的 PDF 页数；日志不包含源文件里的原始页码范围。
- 备注在打印结束后出现。
- `install.sh` 会将旧应用备份到相邻的 `.backup.<时间>` 路径。

## English

A macOS PDF Service for printers without an automatic duplexer. It prepares the PDF for two single-sided passes and prompts you to reload the paper between them.

### Features

- Start it from **PDF → HP 117w Manual Duplex** at the bottom-left of the macOS print dialog.
- Print one side, wait for the sheets to finish, reload the stack when prompted, then print the other side.
- Add an optional note after printing, or skip it.
- Append all records to the `Print Log` sheet in `~/Documents/HP 117w Manual Duplex Print Log.xlsx`.
- Ask whether to open the Excel log after printing; the default is **Not Now**.
- Record the time, supplied PDF name and page count, sheet count, printer, status, and note.
- The log does not include “From Page / To Page”. macOS applies the selected print-dialog range to the PDF passed to the service; this tool records the page count of that supplied PDF.

### Install

1. Add the printer to macOS and confirm that regular printing works.
2. Edit `main.applescript`: set `queueName` to the local CUPS queue name and `printerLabel` to the display name. Run `lpstat -p` to see queue names.
3. Ensure `~/Documents/HP 117w Manual Duplex Print Log.xlsx` exists and has a worksheet named `Print Log` with these headers in A1:G1, in order: `Printed at`, `PDF`, `Pages`, `Sheets`, `Printer`, `Status`, `Notes`.
4. Run:

   ```sh
   ./install.sh
   ```

5. In the macOS print dialog, choose **Edit Menu…** in the PDF menu and enable **HP 117w Manual Duplex**. Reopen the app you print from if the menu has not refreshed.

### Compatibility

This repository is configured for the HP Laser MFP 117w queue and its manual paper reload direction. It uses macOS PDF Services, AppleScript, PDFKit, and CUPS `lp`. Other printers need a valid macOS queue and a calibration of their output and reload direction, even if they accept CUPS single-sided print jobs. Compatibility has not been verified model by model, so no other model is currently listed as supported.

### Limitations

- A4, black and white, one copy, and one page per side are fixed settings.
- The page count is for the PDF received by the service; the log does not include the original document page range.
- The optional note prompt appears after printing.
- `install.sh` backs up an existing app beside it as `.backup.<timestamp>`.
