/**
 * 大众点评 — 自动探索模式 v2
 * 
 * 策略：
 * - 深度优先探索，最大深度 4
 * - 用 activity + 关键节点 hash 做 visited 检测，同一页面不重复进入
 * - 每个页面最多滑 3 次后开始点子元素
 * - 总帧数上限 200，超时 5 分钟自动停
 * - back 操作时深度递减
 */

var CONFIG = {
    apiBase: "http://192.168.0.107:8090",
    dianpingPackage: "com.dianping.v1",
    maxDepth: 4,            // 最大探索深度
    maxFrames: 200,         // 总截图上限
    maxTimeSec: 300,        // 总时长上限（秒）
    maxSwipesPerPage: 3,    // 每页最多滑几次
    swipeInterval: [2000, 4000],
};

// ============ 状态 ============
var visitedPages = {};      // pageHash → true
var depth = 0;
var frameCount = 0;
var startTime = Date.now();

// ============ 工具函数 ============

function pageHash() {
    /** 用 activity + 可见文本的 hash 标识一个页面 */
    var act = "";
    try { act = currentActivity() || ""; } catch(e) {}
    
    var root = auto.root;
    var texts = [];
    if (root) {
        function collect(node, d) {
            if (!node || d > 8 || texts.length > 30) return;
            var t = node.text() || "";
            var desc = node.desc() || "";
            if (t && t.length < 30) texts.push(t);
            if (desc && desc.length < 30) texts.push(desc);
            for (var i = 0; i < node.childCount(); i++) {
                collect(node.child(i), d + 1);
            }
        }
        collect(root, 0);
    }
    // 简单 hash
    var s = act + "|" + texts.slice(0, 20).join(",");
    var h = 0;
    for (var i = 0; i < s.length; i++) {
        h = ((h << 5) - h + s.charCodeAt(i)) | 0;
    }
    return act + "_" + Math.abs(h);
}

function dumpNodes() {
    var nodes = [];
    var root = auto.root;
    if (!root) return nodes;
    function walk(node, d) {
        if (!node || d > 10 || nodes.length > 150) return;
        var t = node.text() || "";
        var dsc = node.desc() || "";
        if (t || dsc || node.clickable() || node.scrollable()) {
            var b = node.bounds();
            nodes.push({
                t: t,
                d: dsc,
                c: node.clickable(),
                s: node.scrollable(),
                b: b ? (b.left + "," + b.top + "," + b.right + "," + b.bottom) : "",
                cls: (node.className() || "").split(".").pop(),
            });
        }
        for (var i = 0; i < node.childCount(); i++) {
            walk(node.child(i), d + 1);
        }
    }
    walk(root, 0);
    return nodes;
}

function sendFrame(action) {
    if (frameCount >= CONFIG.maxFrames) return null;
    if (Date.now() - startTime > CONFIG.maxTimeSec * 1000) return null;

    try {
        var nodes = dumpNodes();
        var tmpPath = "/sdcard/dp_ex_" + Date.now() + ".png";
        var img = captureScreen();
        if (img) {
            images.save(img, tmpPath, "png");
            img.recycle();
        }

        var act = "";
        try { act = currentActivity() || ""; } catch(e) {}

        var res = http.postMultipart(CONFIG.apiBase + "/api/explore", {
            action: action,
            activity: act,
            ui_json: JSON.stringify(nodes),
            depth: depth.toString(),
            ts: Date.now().toString(),
        }, img ? { files: { screen: open(tmpPath) } } : {});

        if (tmpPath && files.exists(tmpPath)) files.remove(tmpPath);
        frameCount++;
        return res.body.json();
    } catch (e) {
        log("sendFrame: " + e);
        return null;
    }
}

// ============ 探索逻辑 ============

function getClickableItems() {
    /** 获取当前页面可点击的元素（排除已知的系统按钮） */
    var items = [];
    var root = auto.root;
    if (!root) return items;

    function collect(node, d) {
        if (!node || d > 10 || items.length > 50) return;
        if (node.clickable()) {
            var t = node.text() || "";
            var dsc = node.desc() || "";
            // 排除系统按钮、导航栏等
            var skip = false;
            if (t === "" && dsc === "") skip = true;
            if (dsc === "返回" || dsc === "更多") skip = true;
            if (t === "确定" || t === "取消") skip = true;
            
            if (!skip) {
                var b = node.bounds();
                items.push({
                    text: t,
                    desc: dsc,
                    bounds: b,
                    x: b ? (b.left + b.right) / 2 : 0,
                    y: b ? (b.top + b.bottom) / 2 : 0,
                });
            }
        }
        for (var i = 0; i < node.childCount(); i++) {
            collect(node.child(i), d + 1);
        }
    }
    collect(root, 0);
    return items;
}

function explorePage() {
    /** 探索当前页面：截图 → 滑几次 → 点进子页面 */
    
    // 检查终止条件
    if (frameCount >= CONFIG.maxFrames) {
        log("达到帧上限 " + CONFIG.maxFrames);
        return;
    }
    if (Date.now() - startTime > CONFIG.maxTimeSec * 1000) {
        log("达到时间上限");
        return;
    }
    if (depth > CONFIG.maxDepth) {
        log("达到深度上限，返回");
        back();
        sleep(1000);
        depth--;
        return;
    }

    // 检测是否已访问
    var hash = pageHash();
    if (visitedPages[hash]) {
        log("页面已访问过: " + hash);
        return;
    }
    visitedPages[hash] = true;

    // 截图 + dump
    sendFrame("enter");
    log("[depth=" + depth + "] 新页面: " + hash);

    // 滑几次看更多内容
    var swipeCount = random(1, CONFIG.maxSwipesPerPage);
    for (var s = 0; s < swipeCount; s++) {
        var sx = random(150, 400);
        var sy = random(1000, 1500);
        var ey = sy - random(200, 500);
        swipe(sx, sy, sx, ey, random(200, 600));
        sleep(random(CONFIG.swipeInterval[0], CONFIG.swipeInterval[1]));
    }

    // 滑动后再截一帧
    sendFrame("after_swipe");

    // 获取可点击元素
    var items = getClickableItems();
    if (items.length === 0) {
        log("没有可点击元素");
        return;
    }

    // 随机选 1-2 个可点击元素进入
    var toExplore = Math.min(items.length, random(1, 2));
    // 随机打乱
    items.sort(function() { return Math.random() - 0.5; });

    for (var i = 0; i < toExplore; i++) {
        if (frameCount >= CONFIG.maxFrames) break;
        if (depth >= CONFIG.maxDepth) break;

        var item = items[i];
        log("点击: " + (item.text || item.desc) + " @ (" + item.x + "," + item.y + ")");
        
        click(item.x, item.y);
        sleep(random(2000, 4000));

        // 检查页面是否变了
        var newHash = pageHash();
        if (newHash !== hash) {
            // 进入了新页面，深度+1，递归探索
            depth++;
            explorePage();  // 递归
        } else {
            log("点击后页面没变，跳过");
        }
    }
}

// ============ 主函数 ============
function startExplore() {
    log("=== 探索模式 v2 启动 ===");
    log("最大深度: " + CONFIG.maxDepth + " | 帧上限: " + CONFIG.maxFrames + " | 时长上限: " + CONFIG.maxTimeSec + "s");

    // 截图权限
    requestScreenCapture(false);
    sleep(500);

    // 启动大众点评
    log("启动大众点评...");
    app.launch(CONFIG.dianpingPackage);
    sleep(5000);

    // 开始递归探索
    depth = 0;
    explorePage();

    // 探索结束，回到首页再截一张
    log("=== 探索完成 ===");
    log("总帧数: " + frameCount);
    log("访问页面数: " + Object.keys(visitedPages).length);
    log("总时长: " + Math.round((Date.now() - startTime) / 1000) + "s");

    // 服务器端可以通过 /api/explore_summary 查看汇总
    try {
        http.get(CONFIG.apiBase + "/api/explore_done?frames=" + frameCount + "&pages=" + Object.keys(visitedPages).length);
    } catch(e) {}
}

startExplore();
