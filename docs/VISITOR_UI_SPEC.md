# 游客端 UI 规范

## UI-01 样图复刻范围

参考文件：

- `docs/ui-references/visitor-mobile-reference-01-home-qa-vision.png`
- `docs/ui-references/visitor-mobile-reference-02-route-journey.png`
- `docs/ui-references/lingshan-button-component-board.png`
- `docs/ui-references/lingshan-custom-icon-board.png`

## 五个 Tab

| Tab | 内容 |
| --- | --- |
| 推荐 | 顶部标题、数字人/占位、主输入框、文化功能按钮、推荐景点 |
| 游灵山 | 用户问题、灵境回答、sources、继续追问、生成路线、播放讲解、反馈不准 |
| 识景 | 上传/预览占位、Top3 候选、确认讲解、换一张、我不确定 |
| 路线 | 自然语言输入、必去/可选/避开、主题分段、生成按钮、路线结果、timeline、扫码带走 |
| 我的 | 路线小票、游中操作、反馈；无路线时显示去路线页生成路线 |

## PNG 图标接入

`frontend/src/components/icons/LingshanImageIcons.tsx` 封装 12 个透明 PNG 图标路径，并提供 `ImageIcon`：

- 支持 `name`、`size`、`className`、`alt`。
- `alt=""` 时设置 `aria-hidden=true`，用于装饰性图标。
- 底部导航、文化功能按钮、路线按钮、source chip、状态按钮优先使用 PNG。

## 底部导航

- 象牙白底，五等分点击区域。
- 图标在上，文字在下。
- 未选中：铜金图标、深褐文字。
- 选中：深松绿圆角矩形，铜金图标、象牙白文字。
- 375px 宽度不得横向滚动。
- 页面底部必须预留空间，避免遮挡关键按钮。

## 功能保持

游客端必须继续可用：

- 文本问答和 sources 展示。
- 发送问题后切换到“游灵山”。
- 识景 Top3 候选确认。
- 自然语言路线规划、必去/可选/避开约束、拥挤度路线。
- 路线分享入口。
- 反馈提交。
- 数字人状态和浏览器 TTS 附属能力。
