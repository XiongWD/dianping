/**
 * 大众点评 — 养号浏览模块 (AutoJs6 兼容)
 */
var config = require("./config.js");

function run() {
    log("开始养号浏览...");
    
    // 1. 打开大众点评
    app.launch(config.dianpingPackage);
    sleep(config.timeout.appLaunch);
    
    // 2. 随机浏览首页
    browseHomepage();
    
    // 3. 随机进入店铺详情
    enterRandomShop();
    
    // 4. 随机点赞
    randomLike();
    
    // 5. 返回首页
    back();
    sleep(500);
    
    log("养号浏览完成");
}

function browseHomepage() {
    var duration = random(config.browseDuration[0], config.browseDuration[1]);
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
    var likeCount = random(config.likePerSession[0], config.likePerSession[1]);
    var liked = 0;
    
    for (var attempt = 0; attempt < likeCount * 3 && liked < likeCount; attempt++) {
        var likeBtn = desc("点赞").findOne(1000);
        if (!likeBtn) {
            likeBtn = text("赞").findOne(1000);
        }
        
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

module.exports = { run: run };
