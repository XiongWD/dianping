/**
 * 眼睛模块 - 截图+控件dump上传到服务器
 * 用法: 在 main.js 里调用 eyes.look("描述")
 * 服务器会自动分析界面并返回操作建议
 */

var SERVER = "http://192.168.0.107:8090";

/**
 * 截屏并上传到服务器分析
 * @param {string} desc 场景描述
 */
function look(desc) {
    log("eyes: 截图中... (" + desc + ")");

    // 1. 截图
    var img = captureScreen();
    if (!img) {
        log("eyes: 截图失败，可能需要授予截图权限");
        requestScreenCapture(false);
        sleep(1000);
        img = captureScreen();
    }
    if (!img) {
        log("eyes: 截图仍然失败");
        return null;
    }

    // 2. 保存截图到临时文件
    var tmpPath = "/sdcard/autojs_eyes_tmp.png";
    images.save(img, tmpPath, "png");
    img.recycle();

    // 3. 上传到服务器
    try {
        var res = http.postMultipart(SERVER + "/api/eyes", {
            description: desc || "unknown",
            screen_time: new Date().toISOString(),
        }, {
            files: {
                screenshot: open(tmpPath),
            },
        });

        var data = res.body.json();
        log("eyes: 分析完成 - " + JSON.stringify(data.summary || data));

        // 清理临时文件
        files.remove(tmpPath);

        return data;
    } catch (e) {
        log("eyes: 上传失败 - " + e);
        return null;
    }
}

/**
 * dump 当前界面的控件树
 */
function dumpUI() {
    var root = auto.root;
    if (!root) {
        log("eyes: 无障碍服务未开启");
        return null;
    }

    var nodes = [];
    function walk(node, depth) {
        if (!node) return;
        var info = {
            className: node.className(),
            text: node.text(),
            desc: node.desc(),
            bounds: node.bounds(),
            clickable: node.clickable(),
            scrollable: node.scrollable(),
            depth: depth,
        };
        nodes.push(info);
        for (var i = 0; i < node.childCount(); i++) {
            walk(node.child(i), depth + 1);
        }
    }
    walk(root, 0);
    return nodes;
}

/**
 * 截图 + 控件dump 一起上传
 */
function analyze(desc) {
    log("eyes: 分析界面... (" + desc + ")");

    // dump 控件
    var uiNodes = dumpUI();
    var uiSummary = [];
    if (uiNodes) {
        // 只取有文字/可点击的关键节点
        for (var i = 0; i < uiNodes.length; i++) {
            var n = uiNodes[i];
            if (n.text || n.desc || n.clickable) {
                uiSummary.push({
                    text: n.text || "",
                    desc: n.desc || "",
                    clickable: n.clickable,
                    scrollable: n.scrollable,
                    bounds: n.bounds ? (n.bounds.left + "," + n.bounds.top + "-" + n.bounds.right + "," + n.bounds.bottom) : "",
                    className: n.className,
                });
            }
        }
    }

    // 截图
    var img = captureScreen();
    var tmpPath = "";
    if (img) {
        tmpPath = "/sdcard/autojs_eyes_tmp.png";
        images.save(img, tmpPath, "png");
        img.recycle();
    }

    // 上传
    try {
        var res = http.postMultipart(SERVER + "/api/eyes", {
            description: desc || "unknown",
            ui_tree: JSON.stringify(uiSummary),
            screen_time: new Date().toISOString(),
        }, tmpPath ? {
            files: {
                screenshot: open(tmpPath),
            },
        } : {});

        var data = res.body.json();
        log("eyes: " + (data.summary || JSON.stringify(data)));

        if (tmpPath) files.remove(tmpPath);
        return data;
    } catch (e) {
        log("eyes: 上传失败 - " + e);
        if (tmpPath) files.remove(tmpPath);
        return null;
    }
}

module.exports = {
    look: look,
    dumpUI: dumpUI,
    analyze: analyze,
};
