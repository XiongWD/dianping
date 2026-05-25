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
                var tmpPath = "/sdcard/dp_eyes_" + Date.now() + ".png";
                images.save(img, tmpPath, "png");
                img.recycle();
                // 读取文件转 base64
                var bytes = files.readBytes(tmpPath);
                importClass("android.util.Base64");
                imgB64 = Base64.encodeToString(bytes, Base64.NO_WRAP);
                files.remove(tmpPath);
                log("eyes: 截图 base64 " + Math.round(imgB64.length / 1024) + "KB");
            }
        }
    } catch (e) {
        log("eyes: 截图异常 - " + e);
    }

    // JSON 上传
    try {
        var payload = {
            description: desc || "unknown",
            ui_tree: JSON.stringify(nodes),
            screen_time: new Date().toISOString(),
            screenshot_b64: imgB64,
        };

        var res = http.post(CONFIG.apiBase + "/api/eyes", JSON.stringify(payload), {
            contentType: "application/json",
            timeout: 30000,
        });

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
var MODES = ["养号浏览", "发布笔记", "连续运行", "截图分析"];

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
    eyesAnalyze("手动截图分析");
}
