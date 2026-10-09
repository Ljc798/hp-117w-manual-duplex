# HP 117w Manual Duplex

[简体中文](#简体中文) | [English](#english)

## 简体中文

一个 macOS PDF 服务，用于没有自动双面器的打印机。它将 PDF 拆成正反两次单面打印，并在两次打印之间提示重新放纸。

### 体验更新

- “打印 / 记录 / 设置”导航：当前流程与主要按钮优先显示，历史和缓存管理独立。
- PDF 逐页图片预览与完整 PDF 打开入口；开始前可选择页码范围、单双面和 1–10 份，并显示预计用纸。
- 多份打印逐份完成放纸流程，后续副本进入待打印列表；每份开始前仍需确认。
- 手机可一次选择多份 PDF，先加入待打印列表；可勾选多份合并成一个打印流程，选择手动双面或单面。列表最多 30 份。批量手动双面会先按列表顺序打印所有正面，再统一放纸打印背面；背面按文件和页码倒序并旋转 180°。单次和批量双面打印都会为奇数页 PDF 自动补空白背面，整叠回纸，无需取出任何纸张。
- 历史记录支持按文件名、备注搜索，以及成功 / 需处理筛选。
- 中断流程显示上次阶段。检查纸张和打印中心后，可结束中断流程，或用新纸重新准备；未完成队列存在时不会重启打印。不会自动从背面继续，避免猜测已出纸数量。
- 设置中的缓存管理显示占用空间；可选择多份未使用 PDF 一次移到 macOS 废纸篓，打印历史保留。正在操作或排队的文件不能清理。

### 手机控制

首次连接后，在 Safari 选择“分享 → 添加到主屏幕”。以后打开固定图标即可，无需重新扫码；Mac 与手机需在同一 Wi-Fi。界面支持中文 / English 切换并记住选择。

- 自动检查打印队列。纸叠出纸时从上到下是最后一页到第一页；按原顺序直接放回进纸器，程序会把背面倒序并旋转 180°。批量时先打印所有正面，再放一次纸打印背面；奇数页文件自动补空白背面，无需取纸。完成后请确认所有页面实际打印成功。
- 步骤显示、纸叠方向示意和奇数页提醒。纸叠按出纸顺序直接放回进纸器；背面页序已自动倒序并旋转 180°。
- 可开启声音提醒（页面在前台时），用于提醒放纸或检查结果。
- 手机上传允许打印的 PDF（最大 50 MB），确认后才开始打印。
- 手机查看打印历史；首次自动读取原有 Excel 日志，新增记录同时写入本机手机历史和原 Excel 日志。
- 从历史记录选择页码范围补打，支持手动双面或单面；必须使用新白纸。页码对应该记录保存的 PDF，选定范围的第一页会作为新的双面序列起点。
- PDF 保存在 `~/Library/Application Support/HP117wMobile/jobs` 供补打使用，打印历史保存在同目录的 SQLite 文件。旧 Excel 记录没有缓存 PDF，只能查看，不能直接补打。
- 服务使用固定口令链接，监听本机与 en0/en1 局域网接口的 8717 端口。链接只交给需要控制打印的人。
- 安装会写入登录启动项 `~/Library/LaunchAgents/local.hp117w.mobile.plist`，登录后即可从手机上传。首次安装可运行 `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.hp117w.mobile.plist`，或重新登录 Mac。
- Mac 需保持开机；打印任务期间防止空闲睡眠，合盖仍可能休眠。若网络地址改变，重启控制服务。

### 功能

- 从 macOS 打印窗口左下角的 **PDF → HP 117w Manual Duplex** 启动。
- 先打印一面，等待纸张打印完成后提示重新放纸，再打印另一面。
- 打印完成后可填写备注，也可以跳过。
- 所有记录追加到 `~/Documents/HP 117w Manual Duplex Print Log.xlsx` 的 `Print Log` 工作表。批量任务每份 PDF 各占一行，同一条可选备注会写入每行。
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

- A4、黑白、每页一面为固定设置。批量打印使用所选文件的完整页数，每份一套；需要选页或打印多份时，逐份预览并设置。
- 页数是 PDF 服务交来的 PDF 页数；日志不包含源文件里的原始页码范围。
- 备注在打印结束后出现。
- `install.sh` 会将旧应用备份到相邻的 `.backup.<时间>` 路径。

## English

A macOS PDF Service for printers without an automatic duplexer. It prepares the PDF for two single-sided passes and prompts you to reload the paper between them.

### Experience update

- **Print / History / Settings** navigation prioritizes the current step and primary action.
- Page-by-page image previews and a full PDF link. Choose a page range, duplex or single-sided mode, and 1–10 copies before starting; see the estimated sheet count.
- Each copy is a separate guided session. Extra copies enter the waiting list; every copy still requires explicit confirmation.
- Select multiple PDFs on your phone and add them to a waiting list (up to 30 documents). Select several and combine them into one print session, choosing manual duplex or single-sided. A duplex batch prints every front in queue order, then prints backs in reverse file and page order, rotated 180°. Odd-page PDFs receive a blank back automatically, for individual and batch duplex jobs. Reload the entire stack without removing sheets.
- Search history by filename or note and filter completed versus unconfirmed/partial records.
- Interrupted workflows show their last stage. After checking paper and Print Center, close the session or prepare it again on fresh paper. Recovery is blocked while unfinished printer jobs remain. The app never guesses which sheets printed or automatically resumes a back-side pass.
- Settings shows cache use and lets you select several unused PDFs to move to macOS Trash at once. Print history stays available. Active and queued sources are protected.

### Phone controls

In Safari, choose **Share → Add to Home Screen** once. Reuse the saved icon for every session; no repeated QR scan. Keep your iPhone and Mac on the same Wi-Fi. The interface supports **中文 / English** and remembers your choice.

- Automatic queue checks and a four-step guide. The stack exits top-to-bottom from last page to first page; reload it directly in the same order. The app reverses and rotates back-side pages by 180°. Odd-page PDFs receive blank backs automatically. Reload all sheets together.
- Optional sound when the page is in the foreground. Queue disappearance does not prove physical success: confirm that all sheets printed before completing a session.
- Upload an unlocked, printable PDF up to 50 MB from your phone. Nothing prints until you confirm.
- Browse history, including a one-time read-only import of the existing Excel log. New records go to local phone history and the existing Excel workflow.
- Reprint a selected range on **fresh blank paper**, either manual duplex or single-sided. Page numbers refer to the saved PDF for that record. A selected range starts a new duplex sequence.
- Saved PDFs live in `~/Library/Application Support/HP117wMobile/jobs`; local history uses SQLite beside it. Old Excel entries without a cached PDF are view-only.
- The fixed link contains a private control token. The service listens on loopback and en0/en1 LAN interfaces, port 8717. Share the link only with people who should control the printer.
- The installer adds `~/Library/LaunchAgents/local.hp117w.mobile.plist` for startup at login. Activate it once with `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.hp117w.mobile.plist` or log in again.
- Keep the Mac awake; the workflow prevents idle sleep while printing, but closing the lid can still suspend it. Restart the service after network address changes.

### Features

- Start it from **PDF → HP 117w Manual Duplex** at the bottom-left of the macOS print dialog.
- Print one side, wait for the sheets to finish, reload the stack when prompted, then print the other side.
- Add an optional note after printing, or skip it.
- Append all records to the `Print Log` sheet in `~/Documents/HP 117w Manual Duplex Print Log.xlsx`. A batch creates one row per PDF; the same optional note is attached to each.
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

- A4, black and white, and one page per side are fixed settings. A batch uses each selected PDF in full, one copy each; review files individually to select ranges or extra copies.
- The page count is for the PDF received by the service; the log does not include the original document page range.
- The optional note prompt appears after printing.
- `install.sh` backs up an existing app beside it as `.backup.<timestamp>`.

## Validation

```sh
HP117W_PDFKIT_TEST=1 python3 -m unittest discover -s tests -v
```

Tests use temporary PDFs and mocked job submissions. They cover duplicate/stale actions, busy-session isolation, PDF range validation, automatic queue monitoring, and real PDFKit front/back ordering and rotation. They do not send print jobs to the physical printer.

手机控制页面地址固定，新打印任务会将 Mac 上已有的 Chrome 或 Safari 控制标签页切到前台；只有找不到时才打开页面。手机仍可使用已收藏的页面或主屏幕图标。

The mobile control URL stays the same. New print sessions bring an existing Chrome or Safari control tab to the front, opening the page only when no matching tab exists. Your iPhone bookmark or Home Screen shortcut still works.

打印页面包含随阶段变化的出纸动画、按钮反馈与页面过渡。动画仅作状态示意，不表示实际页数；可关闭并记住选择，也遵循系统的减少动态效果设置。

The print page includes stage-aware paper animation, button feedback and page transitions. Animation illustrates status rather than actual page counts. Its toggle is remembered, and system reduced-motion preferences are respected.


### Finder 与 DOCX / Finder and DOCX

安装后，Finder 中选中多个 PDF 或 DOCX，右键 → 快速操作或服务 → **HP 117w 打印 — 打开网页**。文件会逐个加入待打印列表，并打开网页；确认后才打印。网页也支持一次上传多个 PDF / DOCX。DOCX 需要 Mac 安装 Microsoft Word，并允许自动化控制 Word。转换临时文件存放在 Word 自己的缓存目录，避免逐个文件夹请求访问权限，处理后自动清理。转换后的 PDF 用于预览、打印和补打；原始文件不修改。部分文件失败时会显示文件名和错误，其余文件继续加入。

After installation, select PDF / DOCX files in Finder, then right-click → Quick Actions or Services → **HP 117w 打印 — 打开网页**. Each file is added to the waiting list and the web controls open. Printing starts after confirmation. Web uploads also accept multiple PDF / DOCX files. DOCX conversion requires Microsoft Word on the Mac and permission to automate Word. Temporary conversion files are stored in Word’s own cache directory to avoid repeated folder access prompts and are cleaned up after processing. Converted PDFs are used for preview, printing and reprints; originals are preserved. Failed files show their names and errors while other files continue to be added.
