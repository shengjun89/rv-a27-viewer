# A27 房车交互模型

在线预览：**https://shengjun89.github.io/rv-a27-viewer/**

基于 A27 CAD 的 13 类活动部件、额头床及窗框参考线，可在电脑和手机浏览器中旋转、缩放和播放。

## 操作

- 柜门：点击打开并保持，再次点击关闭。转动期间忽略重复触发，每次点击只执行一段动作。
- 工作台、沙发、梯子、卫浴卷门：点击播放完整演示并复位；播放中再次点击可提前沿原路径恢复。
- 拖动旋转，双指缩放或平移；顶部提供复位、俯视、缩放和分享。

工作台包含琴托、61 键 MIDI、办公椅和沙发成床联动；梯子按折踏板、直立缩短、横推入柜、关门锁止的顺序收纳。柜门使用各自的 CAD 铰轴。

速度以 CAD 原演示为基准：柜门 6 倍，其余 5 倍。柜门单程采用原始往返中 37% 的动作段；工作台整段 4.4 秒，梯子整段 6 秒，卫浴卷门 1.4 秒。这里展示的是模型动作，不是实车承载或施工验收结论。

## 本地运行

需要 Node.js 22 及 Python 3。

```sh
npm ci
npm test
npm run build
npm run dev
```

打开 http://localhost:4173/ 。

## 自动发布

推送到 `main` 后，GitHub Actions 自动安装依赖、验证模型动作、构建并发布到 GitHub Pages。页面和模型均使用相对资源路径，支持仓库子目录。

`src/` 为 Three.js 播放器，`public/rv-a27.glb` 为几何模型，`public/motion-data.json` 为 CAD 动作数据，`public/model-info.json` 为版本、时长和资源哈希。`test/fixtures/cad-checks.json` 保留用于核对铰轴及动作顺序的 CAD 样本。
