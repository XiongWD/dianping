/**
 * 大众点评 — 发布笔记模块
 */
var config = require("./config.js");

var PACK = null; // 当前内容包

/**
 * 运行发布流程
 */
function run() {
    // 1. 从服务器获取内容包
    toast("正在从服务器获取内容...");
    var pack = fetchContentPack();
    if (!pack) {
        toast("没有待发布的内容");
        return false;
    }
    
    PACK = pack;
    toast("获取成功: " + pack.shop_name);
    
    // 2. 执行发布
    return runSingle(pack);
}

/**
 * 发布单条笔记
 */
function runSingle(pack) {
    if (!pack) {
        pack = fetchContentPack();
        if (!pack) return false;
    }
    
    log("开始发布: " + pack.title);
    
    // 1. 打开大众点评
    launchDianping();
    sleep(3000);
    
    // 2. 点击"发笔记"
    if (!clickPublishButton()) {
        toast("未找到发布按钮");
        return false;
    }
    sleep(1500);
    
    // 3. 上传图片（如果有本地图片）
    // 注意：手机端图片需要先下载到本地
    // 后续版本实现
    
    // 4. 输入文案
    inputContent(pack.content);
    sleep(500);
    
    // 5. 输入标题
    inputTitle(pack.title);
    sleep(500);
    
    // 6. 添加话题
    addTopic("创作者赏金计划");
    sleep(500);
    
    // 7. 关联店铺
    searchShop(pack.shop_name);
    sleep(1000);
    
    // 8. 点击发布
    clickSubmitButton();
    sleep(3000);
    
    // 9. 上报结果
    reportResult(pack.pack_id, "published", {title: pack.title});
    
    toast("发布完成: " + pack.title);
    return true;
}

/**
 * 从服务器获取内容包
 */
function fetchContentPack() {
    try {
        var url = config.apiBase + "/api/packs?limit=1";
        var res = http.get(url, {timeout: 10000});
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

/**
 * 打开大众点评 APP
 */
function launchDianping() {
    log("启动大众点评...");
    app.launch(config.dianpingPackage);
    sleep(config.timeout.appLaunch);
    
    // 等待首页加载
    waitForActivity("com.dianping.v1.*", config.timeout.appLaunch);
}

/**
 * 点击"发笔记"按钮
 */
function clickPublishButton() {
    // 方案1: 找"发笔记"文字按钮
    var btn = text("发笔记").findOne(3000);
    if (btn) {
        btn.click();
        return true;
    }
    
    // 方案2: 找"+"号按钮
    btn = desc("发布").findOne(2000);
    if (btn) {
        btn.click();
        return true;
    }
    
    // 方案3: 找图（备选方案）
    // var img = captureScreen();
    // var match = findImage(img, readImage("./publish_btn.png"));
    
    return false;
}

/**
 * 输入文案内容
 */
function inputContent(content) {
    // 找到内容输入框
    var editText = className("EditText").findOne(3000);
    if (editText) {
        editText.setText(content);
        return true;
    }
    return false;
}

/**
 * 输入标题
 */
function inputTitle(title) {
    // 找到标题输入框（通常 hint 包含"添加标题"）
    var titleInput = textContains("标题").className("EditText").findOne(2000);
    if (titleInput) {
        titleInput.setText(title);
        return true;
    }
    return false;
}

/**
 * 添加话题
 */
function addTopic(topicName) {
    // 点击添加话题
    var topicBtn = textContains("话题").findOne(2000);
    if (topicBtn) {
        topicBtn.click();
        sleep(500);
        
        // 输入话题
        var input = className("EditText").findOne(2000);
        if (input) {
            input.setText(topicName);
            sleep(1000);
            
            // 选择搜索结果第一个
            var result = textContains(topicName).findOne(2000);
            if (result) {
                result.click();
            }
        }
    }
}

/**
 * 搜索关联店铺
 */
function searchShop(shopName) {
    var shopBtn = textContains("门店").findOne(2000);
    if (shopBtn) {
        shopBtn.click();
        sleep(500);
        
        var input = className("EditText").findOne(2000);
        if (input) {
            input.setText(shopName);
            sleep(2000);
            
            // 选择第一个搜索结果
            var result = textContains(shopName.substring(0, 4)).findOne(3000);
            if (result) {
                result.click();
            }
        }
    }
}

/**
 * 点击发布/提交按钮
 */
function clickSubmitButton() {
    var btn = text("发布").findOne(3000);
    if (!btn) {
        btn = text("提交").findOne(2000);
    }
    if (btn) {
        btn.click();
        return true;
    }
    return false;
}

/**
 * 上报发布结果
 */
function reportResult(packId, status, result) {
    try {
        var url = config.apiBase + "/api/report";
        http.postJson(url, {
            pack_id: packId,
            status: status,
            result: result || {},
        });
    } catch (e) {
        log("上报失败: " + e);
    }
}

module.exports = {
    run: run,
    runSingle: runSingle,
};
