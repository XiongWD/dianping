/**
 * 大众点评 — 发布笔记模块 (AutoJs6 兼容)
 */
var config = require("./config.js");

function run() {
    toast("正在从服务器获取内容...");
    var pack = fetchContentPack();
    if (!pack) {
        toast("没有待发布的内容");
        return false;
    }
    
    toast("获取成功: " + pack.shop_name);
    return runSingle(pack);
}

function runSingle(pack) {
    if (!pack) {
        pack = fetchContentPack();
        if (!pack) return false;
    }
    
    log("开始发布: " + pack.title);
    
    // 1. 打开大众点评
    app.launch(config.dianpingPackage);
    sleep(3000);
    
    // 2. 点击"发笔记"
    if (!clickPublishButton()) {
        toast("未找到发布按钮");
        return false;
    }
    sleep(1500);
    
    // 3. 输入文案
    inputContent(pack.content);
    sleep(500);
    
    // 4. 输入标题
    inputTitle(pack.title);
    sleep(500);
    
    // 5. 添加话题
    addTopic("创作者赏金计划");
    sleep(500);
    
    // 6. 关联店铺
    if (pack.shop_name) {
        searchShop(pack.shop_name);
    }
    sleep(1000);
    
    // 7. 点击发布
    clickSubmitButton();
    sleep(3000);
    
    // 8. 上报结果
    reportResult(pack.pack_id, "published");
    
    toast("发布完成: " + pack.title);
    return true;
}

function fetchContentPack() {
    try {
        var url = config.apiBase + "/api/packs?limit=1";
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
    if (editText) {
        editText.setText(content);
        return true;
    }
    return false;
}

function inputTitle(title) {
    var titleInput = textContains("标题").className("EditText").findOne(2000);
    if (titleInput) {
        titleInput.setText(title);
        return true;
    }
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
    var btn = text("发布").findOne(3000);
    if (!btn) btn = text("提交").findOne(2000);
    if (btn) { btn.click(); return true; }
    return false;
}

function reportResult(packId, status) {
    try {
        var url = config.apiBase + "/api/report";
        http.postJson(url, {
            pack_id: packId,
            status: status,
            result: {}
        });
    } catch (e) {
        log("上报失败: " + e);
    }
}

module.exports = { run: run, runSingle: runSingle };
