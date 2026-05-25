/**
 * 大众点评自动发布脚本 — AutoJs6 主入口
 */
var config = require("./config.js");
var browse = require("./browse.js");
var publish = require("./publish.js");

var MODES = ["养号浏览", "发布笔记", "连续运行"];

function showMenu() {
    var options = MODES;
    dialogs.singleChoice("选择运行模式", options, 0)
        .then(function(choice) {
            if (choice < 0) {
                toast("已取消");
                return;
            }
            switch (choice) {
                case 0:
                    toast("启动养号浏览模式");
                    browse.run();
                    break;
                case 1:
                    toast("启动发布笔记模式");
                    publish.run();
                    break;
                case 2:
                    toast("启动连续运行模式");
                    runLoop();
                    break;
            }
        });
}

function runLoop() {
    var interval = config.publishInterval || 30;
    var count = 0;
    var maxCount = config.maxPublishPerDay || 5;
    
    toast("连续运行: 每 " + interval + " 分钟发布，每天最多 " + maxCount + " 条");
    
    while (count < maxCount) {
        browse.run();
        var success = publish.runSingle();
        if (success) {
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

// 启动
showMenu();
