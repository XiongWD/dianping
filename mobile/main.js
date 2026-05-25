/**
 * 大众点评自动脚本 — 单文件版 (AutoJs6)
 * 养号浏览 / 发布笔记 / 连续运行
 */

// ============ 配置 ============
var CONFIG = {
    apiBase: "http://192.168.0.107:8090",
    publishInterval: 30,
    maxPublishPerDay: 5,
    browseDuration: [3, 5],
    likePerSession: [2, 5],
    dianpingPackage: "com.dianping.v1",
    timeout: {
        appLaunch: 10000,
        pageLoad: 5000,
        upload: 30000,
    },
};

// ============ 养号浏览 ============
function browseRun() {
    log("开始养号浏览...");
    app.launch(CONFIG.dianpingPackage);
    sleep(CONFIG.timeout.appLaunch);

    browseHomepage();
    enterRandomShop();
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
        var distance = random(300, 600);
        var startX = random(300, 500);
        var startY = random(1200, 1600);
        var endY = startY - distance;
        swipe(startX, startY, startX, endY, random(300, 800));
        sleep(random(2000, 5000));

        if (random(1, 10) > 7) {
            var item = className("android.widget.RelativeLayout").findOne(2000);
            if (item) {
                item.click();
                sleep(random(5000, 15000));
                scrollDown();
                sleep(random(2000, 4000));
                back();
                sleep(1000);
            }
        }
    }
}

function enterRandomShop() {
    var shopCards = textContains("人均").find();
    if (shopCards && shopCards.length > 0) {
        var idx = random(0, Math.min(shopCards.length - 1, 5));
        shopCards[idx].click();
        sleep(3000);
        for (var i = 0; i < random(2, 4); i++) {
            scrollDown();
            sleep(random(2000, 4000));
        }
        back();
        sleep(1000);
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
    if (!pack) {
        toast("没有待发布的内容");
        return false;
    }
    toast("获取成功: " + pack.shop_name);
    return publishSingle(pack);
}

function publishSingle(pack) {
    if (!pack) {
        pack = fetchContentPack();
        if (!pack) return false;
    }

    log("开始发布: " + pack.title);

    app.launch(CONFIG.dianpingPackage);
    sleep(3000);

    if (!clickPublishButton()) {
        toast("未找到发布按钮");
        return false;
    }
    sleep(1500);

    inputContent(pack.content);
    sleep(500);

    inputTitle(pack.title);
    sleep(500);

    addTopic("创作者赏金计划");
    sleep(500);

    if (pack.shop_name) {
        searchShop(pack.shop_name);
    }
    sleep(1000);

    clickSubmitButton();
    sleep(3000);

    reportResult(pack.pack_id, "published");
    toast("发布完成: " + pack.title);
    return true;
}

function fetchContentPack() {
    try {
        var url = CONFIG.apiBase + "/api/packs?limit=1";
        var res = http.get(url, { timeout: 10000 });
        var data = res.body.json();
        if (data.packs && data.packs.length > 0) {
            return data.packs[0];
        }
        return null;
    } catch (e) {
        log("获取内容失败: " + e);
        return null;
    }
}

function clickPublishButton() {
    var btn = text("发笔记").findOne(3000);
    if (btn) { btn.click(); return true; }
    btn = desc("发布").findOne(2000);
    if (btn) { btn.click(); return true; }
    return false;
}

function inputContent(content) {
    var editText = className("EditText").findOne(3000);
    if (editText) { editText.setText(content); return true; }
    return false;
}

function inputTitle(title) {
    var titleInput = textContains("标题").className("EditText").findOne(2000);
    if (titleInput) { titleInput.setText(title); return true; }
    return false;
}

function addTopic(topicName) {
    var topicBtn = textContains("话题").findOne(2000);
    if (topicBtn) {
        topicBtn.click();
        sleep(500);
        var input = className("EditText").findOne(2000);
        if (input) {
            input.setText(topicName);
            sleep(1000);
            var result = textContains(topicName).findOne(2000);
            if (result) result.click();
        }
    }
}

function searchShop(shopName) {
    var shopBtn = textContains("门店").findOne(2000);
    if (shopBtn) {
        shopBtn.click();
        sleep(500);
        var input = className("EditText").findOne(2000);
        if (input) {
            input.setText(shopName);
            sleep(2000);
            var result = textContains(shopName.substring(0, 4)).findOne(3000);
            if (result) result.click();
        }
    }
}

function clickSubmitButton() {
    var btn = text("发布").findOne(3000) || text("提交").findOne(2000);
    if (btn) { btn.click(); return true; }
    return false;
}

function reportResult(packId, status) {
    try {
        http.postJson(CONFIG.apiBase + "/api/report", {
            pack_id: packId,
            status: status,
            result: {}
        });
    } catch (e) {
        log("上报失败: " + e);
    }
}

// ============ 连续运行 ============
function runLoop() {
    var interval = CONFIG.publishInterval;
    var count = 0;
    var maxCount = CONFIG.maxPublishPerDay;

    toast("连续运行: 每 " + interval + " 分钟发布，每天最多 " + maxCount + " 条");

    while (count < maxCount) {
        browseRun();
        if (publishSingle()) {
            count++;
            toast("已发布 " + count + "/" + maxCount);
        }
        if (count < maxCount) {
            var waitMinutes = interval + random(-5, 10);
            toast("等待 " + waitMinutes + " 分钟...");
            sleep(waitMinutes * 60 * 1000);
        }
    }
    toast("今日任务完成");
}

// ============ 入口 ============
var MODES = ["养号浏览", "发布笔记", "连续运行"];

var choice = dialogs.singleChoice("选择运行模式", MODES, 0);
if (choice < 0) { toast("已取消"); }
else if (choice === 0) { browseRun(); }
else if (choice === 1) { publishRun(); }
else if (choice === 2) { runLoop(); }
