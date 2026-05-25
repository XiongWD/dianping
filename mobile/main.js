/**
 * 大众点评自动发布脚本 — AutoX.js
 * 主入口
 */
var config = require("./config.js");
var publish = require("./publish.js");
var browse = require("./browse.js");

// 脚本菜单
var MODES = {
    "1": "养号浏览（随机浏览+点赞）",
    "2": "发布笔记（从服务器拉取内容）",
    "3": "连续运行（养号+发布循环）",
};

function showMenu() {
    var options = [];
    for (var key in MODES) {
        options.push(key + ". " + MODES[key]);
    }
    var choice = dialogs.singleChoice("选择模式", options, 0);
    
    switch (choice) {
        case 0:
            browse.run();
            break;
        case 1:
            publish.run();
            break;
        case 2:
            runLoop();
            break;
    }
}

function runLoop() {
    // 连续运行模式
    var interval = config.publishInterval || 30; // 分钟
    var count = 0;
    var maxCount = config.maxPublishPerDay || 5;
    
    toast("连续运行模式启动");
    toast("每 " + interval + " 分钟发布一条，每天最多 " + maxCount + " 条");
    
    while (count < maxCount) {
        // 先养号浏览
        browse.run();
        
        // 再发布
        var success = publish.runSingle();
        if (success) {
            count++;
            toast("已发布 " + count + "/" + maxCount);
        }
        
        // 等待间隔
        if (count < maxCount) {
            var waitMinutes = interval + random(-5, 10);
            toast("等待 " + waitMinutes + " 分钟后继续...");
            sleep(waitMinutes * 60 * 1000);
        }
    }
    
    toast("今日发布任务完成");
}

// 启动
showMenu();
