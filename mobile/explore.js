/**
 * 大众点评 — 自动探索模式
 * 自动打开APP → 截图+dump节点 → 滑动/点击 → 持续回传服务器
 * 服务器端积累数据后自动分析界面结构
 */

var CONFIG = {
    apiBase: "http://192.168.0.107:8090",
    dianpingPackage: "com.dianping.v1",
    exploreDuration: 300,       // 探索总时长（秒）
    screenshotInterval: 3,      // 每隔几秒截一次图
    tapProbability: 0.15,       // 每次滑动后点击概率
    swipeInterval: [2000, 5000], // 滑动间隔（毫秒）
};

// ============ 截图+节点上传 ============
function sendFrame(action) {
    try {
        // dump 控件节点
        var uiNodes = [];
        var root = auto.root;
        if (root) {
            function walk(node, depth) {
                if (!node || depth > 12 || uiNodes.length > 200) return;
                var t = node.text() || "";
                var d = node.desc() || "";
                if (t || d || node.clickable() || node.scrollable()) {
                    var b = node.bounds();
                    uiNodes.push({
                        t: t,
                        d: d,
                        c: node.clickable(),
                        s: node.scrollable(),
                        b: b ? (b.left + "," + b.top + "," + b.right + "," + b.bottom) : "",
                        cls: (node.className() || "").split(".").pop(),
                    });
                }
                for (var i = 0; i < node.childCount(); i++) {
                    walk(node.child(i), depth + 1);
                }
            }
            walk(root, 0);
        }

        // 截图
        var tmpPath = "/sdcard/dp_explore_" + Date.now() + ".png";
        var img = captureScreen();
        if (img) {
            images.save(img, tmpPath, "png");
            img.recycle();
        }

        // 当前 activity
        var activity = "";
        try { activity = currentActivity() || ""; } catch(e) {}

        var res = http.postMultipart(CONFIG.apiBase + "/api/explore", {
            action: action || "auto",
            activity: activity,
            ui_json: JSON.stringify(uiNodes),
            ts: Date.now().toString(),
        }, (img ? { files: { screen: open(tmpPath) } } : {}));

        if (tmpPath && files.exists(tmpPath)) files.remove(tmpPath);
        return res.body.json();
    } catch (e) {
        log("sendFrame err: " + e);
        return null;
    }
}

// ============ 主探索流程 ============
function startExplore() {
    log("=== 探索模式启动 ===");
    log("将自动截图、滑动、点击，数据回传服务器");

    // 请求截图权限
    if (!requestScreenCapture(false)) {
        // 有些版本 requestScreenCapture 是异步的
    }
    sleep(500);

    // 启动大众点评
    log("启动大众点评...");
    app.launch(CONFIG.dianpingPackage);
    sleep(5000);

    // 先截第一帧
    sendFrame("launch");
    log("首帧已上传");

    var startTime = Date.now();
    var endTime = startTime + CONFIG.exploreDuration * 1000;
    var frameCount = 1;
    var lastScreenshot = startTime;

    while (Date.now() < endTime) {
        var now = Date.now();

        // 每隔 screenshotInterval 秒截一次
        if (now - lastScreenshot >= CONFIG.screenshotInterval * 1000) {
            sendFrame("auto");
            frameCount++;
            lastScreenshot = now;

            if (frameCount % 10 === 0) {
                log("已采集 " + frameCount + " 帧");
            }
        }

        // 随机操作
        var op = Math.random();

        if (op < 0.6) {
            // 滑动
            var sx = random(150, 400);
            var sy = random(1000, 1500);
            var ey = sy - random(200, 500);
            swipe(sx, sy, sx, ey, random(200, 600));
        } else if (op < 0.7) {
            // 上滑（看更多内容）
            var sx2 = random(150, 400);
            var sy2 = random(400, 600);
            var ey2 = sy2 + random(200, 500);
            swipe(sx2, sy2, sx2, ey2, random(200, 600));
        } else if (op < 0.7 + CONFIG.tapProbability) {
            // 随机点击屏幕中间区域
            var tx = random(100, 350);
            var ty = random(300, 1200);
            click(tx, ty);
            log("点击 (" + tx + "," + ty + ")");
            sleep(random(2000, 4000));
            // 点进去后也截图
            sendFrame("tap");
        } else if (op < 0.92) {
            // back
            back();
            sleep(1000);
        } else {
            // 停留
            sleep(random(1000, 3000));
        }

        sleep(random(CONFIG.swipeInterval[0], CONFIG.swipeInterval[1]));
    }

    log("=== 探索完成，共 " + frameCount + " 帧 ===");
}

// ============ 入口 ============
startExplore();
