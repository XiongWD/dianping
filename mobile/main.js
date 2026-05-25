/**
 * 大众点评自动脚本 — 单文件版 (AutoJs6)
 * 截图+节点 → base64 JSON上传，不用 multipart
 */

// ============ 截图权限（必须在最顶层请求） ============
var screenCaptureReady = false;
try {
    screenCaptureReady = requestScreenCapture(false);
    log("截图权限: " + screenCaptureReady);
} catch (e) {
    log("截图权限请求失败: " + e);
}

// ============ 配置 ============
var CONFIG = {
    apiBase: "http://192.168.0.107:8090",
    publishInterval: 30,
    maxPublishPerDay: 5,
    browseDuration: [1, 3],
    likePerSession: [1, 3],
    dianpingPackage: "com.dianping.v1",
    timeout: {
        appLaunch: 10000,
        pageLoad: 5000,
        upload: 30000,
    },
};

// ============ dump控件 ============
function dumpUI() {
    var root = auto.root;
    if (!root) return [];
    var nodes = [];
    function walk(node, depth) {
        if (!node || depth > 12 || nodes.length > 150) return;
        var t = node.text() || "";
        var d = node.desc() || "";
        if (t || d || node.clickable() || node.scrollable()) {
            var b = node.bounds();
            nodes.push({
                t: t, d: d,
                c: node.clickable(), s: node.scrollable(),
                b: b ? (b.left + "," + b.top + "," + b.right + "," + b.bottom) : "",
                cls: (node.className() || "").split(".").pop(),
            });
        }
        for (var i = 0; i < node.childCount(); i++) {
            walk(node.child(i), depth + 1);
        }
    }
    walk(root, 0);
    return nodes;
}

// ============ 截图+上传（base64 JSON 方式） ============
function eyesAnalyze(desc) {
    log("eyes: 分析界面... (" + desc + ")");

    // dump 节点
    var nodes = dumpUI();
    log("eyes: " + nodes.length + " 个节点");

    // 截图
    var imgB64 = "";
    try {
        if (screenCaptureReady) {
            var img = captureScreen();
            if (img) {
                // 缩小到 540 宽，降低质量，控制大小在 200KB 以内
                var w = img.getWidth();
                var h = img.getHeight();
                var scale = 540.0 / w;
                var smallImg = images.scale(img, scale, scale);
                img.recycle();
                var tmpPath = "/sdcard/dp_eyes_" + Date.now() + ".jpg";
                images.save(smallImg, tmpPath, "jpg", 60);  // quality=60
                smallImg.recycle();
                // 读取文件转 base64
                var bytes = files.readBytes(tmpPath);
                importClass("android.util.Base64");
                imgB64 = Base64.encodeToString(bytes, Base64.NO_WRAP);
                files.remove(tmpPath);
                log("eyes: 截图 base64 " + Math.round(imgB64.length / 1024) + "KB (" + Math.round(w * scale) + "x" + Math.round(h * scale) + ")");
            }
        }
    } catch (e) {
        log("eyes: 截图异常 - " + e);
    }

    // JSON 上传
    try {
        // 先测试连通性
        var testRes = http.get(CONFIG.apiBase + "/api/status", { timeout: 5000 });
        log("eyes: 连通测试 " + (testRes && testRes.statusCode === 200 ? "OK" : "FAIL"));
    } catch (e) {
        log("eyes: 连通测试失败 - " + e);
        return null;
    }

    try {
        var payload = {
            description: desc || "unknown",
            ui_tree: JSON.stringify(nodes),
            screen_time: new Date().toISOString(),
            screenshot_b64: imgB64,
        };

        var res = http.postJson(CONFIG.apiBase + "/api/eyes", payload);

        var data = res.body.json();
        log("eyes: " + (data.summary || JSON.stringify(data)));
        return data;
    } catch (e) {
        log("eyes: 上传失败 - " + e);
        return null;
    }
}

// ============ 养号浏览 ============
function browseRun() {
    log("开始养号浏览...");
    var currentPkg = currentPackage();
    if (currentPkg !== CONFIG.dianpingPackage) {
        app.launch(CONFIG.dianpingPackage);
        sleep(CONFIG.timeout.appLaunch);
    }

    eyesAnalyze("首页浏览");
    browseHomepage();
    randomLike();

    back();
    sleep(500);
    log("养号浏览完成");
}

function browseHomepage() {
    var duration = random(CONFIG.browseDuration[0], CONFIG.browseDuration[1]);
    var endTime = Date.now() + duration * 60 * 1000;
    log("浏览首页，持续 " + duration + " 分钟");

    while (Date.now() < endTime) {
        var startX = random(200, 400);
        var startY = random(1200, 1600);
        var endY = startY - random(300, 600);
        swipe(startX, startY, startX, endY, random(300, 800));
        sleep(random(3000, 6000));

        if (random(1, 10) > 7) {
            var item = className("android.widget.RelativeLayout").findOne(2000);
            if (item) {
                item.click();
                sleep(random(3000, 8000));
                scrollDown();
                sleep(random(1000, 3000));
                back();
                sleep(1000);
            }
        }
    }
}

function randomLike() {
    var likeCount = random(CONFIG.likePerSession[0], CONFIG.likePerSession[1]);
    var liked = 0;
    for (var attempt = 0; attempt < likeCount * 3 && liked < likeCount; attempt++) {
        var likeBtn = desc("点赞").findOne(1000) || text("赞").findOne(1000);
        if (likeBtn) {
            likeBtn.click();
            liked++;
            sleep(random(1000, 3000));
        }
        scrollDown();
        sleep(500);
    }
    log("点赞 " + liked + " 条");
}

// ============ 发布笔记 ============
function publishRun() {
    toast("正在从服务器获取内容...");
    var pack = fetchContentPack();
    if (!pack) { toast("没有待发布的内容"); return false; }
    toast("获取成功: " + pack.shop_name);
    return publishSingle(pack);
}

function publishSingle(pack) {
    if (!pack) { pack = fetchContentPack(); if (!pack) return false; }
    log("开始发布: " + pack.title);

    app.launch(CONFIG.dianpingPackage);
    sleep(3000);

    if (!clickPublishButton()) {
        toast("未找到发布按钮");
        eyesAnalyze("发布按钮未找到");
        return false;
    }
    sleep(1500);

    inputContent(pack.content);
    sleep(500);
    inputTitle(pack.title);
    sleep(500);
    addTopic("创作者赏金计划");
    sleep(500);
    if (pack.shop_name) searchShop(pack.shop_name);
    sleep(1000);

    clickSubmitButton();
    sleep(3000);

    reportResult(pack.pack_id, "published");
    toast("发布完成: " + pack.title);
    return true;
}

function fetchContentPack() {
    try {
        var res = http.get(CONFIG.apiBase + "/api/packs?limit=1", { timeout: 10000 });
        var data = res.body.json();
        if (data.packs && data.packs.length > 0) return data.packs[0];
        return null;
    } catch (e) { log("获取内容失败: " + e); return null; }
}

function clickPublishButton() {
    var btn = text("发笔记").findOne(3000);
    if (btn) { btn.click(); return true; }
    btn = desc("发布").findOne(2000);
    if (btn) { btn.click(); return true; }
    return false;
}

function inputContent(content) {
    var et = className("EditText").findOne(3000);
    if (et) { et.setText(content); return true; }
    return false;
}

function inputTitle(title) {
    var ti = textContains("标题").className("EditText").findOne(2000);
    if (ti) { ti.setText(title); return true; }
    return false;
}

function addTopic(topicName) {
    var tb = textContains("话题").findOne(2000);
    if (tb) {
        tb.click(); sleep(500);
        var inp = className("EditText").findOne(2000);
        if (inp) { inp.setText(topicName); sleep(1000); var r = textContains(topicName).findOne(2000); if (r) r.click(); }
    }
}

function searchShop(shopName) {
    var sb = textContains("门店").findOne(2000);
    if (sb) {
        sb.click(); sleep(500);
        var inp = className("EditText").findOne(2000);
        if (inp) { inp.setText(shopName); sleep(2000); var r = textContains(shopName.substring(0, 4)).findOne(3000); if (r) r.click(); }
    }
}

function clickSubmitButton() {
    var btn = text("发布").findOne(3000) || text("提交").findOne(2000);
    if (btn) { btn.click(); return true; }
    return false;
}

function reportResult(packId, status) {
    try { http.postJson(CONFIG.apiBase + "/api/report", { pack_id: packId, status: status, result: {} }); } catch (e) { log("上报失败: " + e); }
}

// ============ 数据采集 ============
function collectRun() {
    log("采集模式启动");
    toast("数据采集模式：自动浏览+截图");

    // 检查无障碍服务
    if (!auto.service) {
        log("无障碍服务未运行，尝试启用...");
        try {
            auto.waitFor(5000);
        } catch (e) {
            log("无障碍服务启用失败: " + e);
            toast("请手动开启无障碍服务后重试");
            return;
        }
    }
    log("无障碍服务: OK");

    // 确保在大众点评
    var currentPkg = currentPackage();
    if (currentPkg !== CONFIG.dianpingPackage) {
        log("启动大众点评...");
        app.launch(CONFIG.dianpingPackage);
        sleep(CONFIG.timeout.appLaunch);
    }

    var totalShots = 0;
    var maxShots = 20;  // 一轮最多20张
    var pages = ["首页", "商家详情"];  // 先覆盖这两个

    // ===== 首页采集 =====
    log("--- 首页采集 ---");
    // 首页上滑3次，每次截一张
    eyesAnalyze("首页-初始");
    totalShots++;
    for (var i = 0; i < 3 && totalShots < maxShots; i++) {
        var sx = random(200, 400);
        var sy = random(1200, 1600);
        swipe(sx, sy, sx, sy - random(400, 700), random(400, 800));
        sleep(random(2000, 4000));
        eyesAnalyze("首页-滑动" + (i + 1));
        totalShots++;
    }

    // ===== 点击进商家详情 =====
    log("--- 商家详情采集 ---");
    // 回到顶部
    swipe(300, 500, 300, 1500, 300);
    sleep(1000);

    // 尝试点击前3个商家
    for (var shopIdx = 0; shopIdx < 3 && totalShots < maxShots; shopIdx++) {
        // 查找可点击的内容卡片（通常有图片+文字）
        var card = className("android.widget.RelativeLayout").clickable(true).findOne(3000);
        if (!card) {
            log("未找到可点击的商家卡片");
            break;
        }

        var cardBounds = card.bounds();
        log("点击商家卡片 @ " + cardBounds);
        click(cardBounds.centerX(), cardBounds.centerY());
        sleep(random(3000, 5000));

        // 检查是否进入了商家详情页
        var isDetail = textContains("地址").findOne(2000) || textContains("人均").findOne(2000) || textContains("营业").findOne(2000);
        if (isDetail) {
            log("进入商家详情页");
            // 商家详情页截图
            eyesAnalyze("商家详情-顶部");
            totalShots++;

            // 向下滑动2次
            for (var j = 0; j < 2 && totalShots < maxShots; j++) {
                scrollDown();
                sleep(random(2000, 3000));
                eyesAnalyze("商家详情-滑动" + (j + 1));
                totalShots++;
            }

            // 返回首页
            back();
            sleep(random(2000, 3000));
        } else {
            log("未进入商家详情，返回");
            back();
            sleep(1000);
        }

        // 滑动到下一个卡片
        swipe(300, 1200, 300, 600, 500);
        sleep(1000);
    }

    log("采集完成，共 " + totalShots + " 张");
    toast("采集完成：" + totalShots + " 张截图");
}

// ============ 连续运行 ============
function runLoop() {
    var interval = CONFIG.publishInterval;
    var count = 0;
    var maxCount = CONFIG.maxPublishPerDay;
    toast("连续运行: 每 " + interval + " 分钟发布，最多 " + maxCount + " 条");
    while (count < maxCount) {
        browseRun();
        if (publishSingle()) { count++; toast("已发布 " + count + "/" + maxCount); }
        if (count < maxCount) { var w = interval + random(-5, 10); toast("等待 " + w + " 分钟..."); sleep(w * 60 * 1000); }
    }
    toast("今日任务完成");
}

// ============ 入口 ============
var MODES = ["养号浏览", "发布笔记", "连续运行", "截图分析", "数据采集"];

var choice = dialogs.singleChoice("选择运行模式", MODES, 0);
if (choice < 0) { toast("已取消"); }
else if (choice === 0) { browseRun(); }
else if (choice === 1) { publishRun(); }
else if (choice === 2) { runLoop(); }
else if (choice === 3) {
    var currentPkg = currentPackage();
    if (currentPkg !== CONFIG.dianpingPackage) {
        log("当前不是大众点评，正在启动...");
        app.launch(CONFIG.dianpingPackage);
        sleep(CONFIG.timeout.appLaunch);
    }
    eyesAnalyze("截图分析");
}
else if (choice === 4) { collectRun(); }
