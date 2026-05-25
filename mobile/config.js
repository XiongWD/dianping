/**
 * 配置文件 - AutoJs6 兼容
 */
var config = {};

config.apiBase = "http://192.168.0.107:8090";

// 发布设置
config.publishInterval = 30;       // 发布间隔（分钟）
config.maxPublishPerDay = 5;       // 每天最多发布条数
config.imageCount = [3, 6];        // 图片数量范围

// 养号设置
config.browseDuration = [3, 5];    // 浏览时长范围（分钟）
config.browseSessions = 3;         // 每天浏览次数
config.likePerSession = [2, 5];    // 每次点赞数范围

// 大众点评包名
config.dianpingPackage = "com.dianping.v1";

// 发布时间段
config.publishTimes = [
    "11:30", "12:30", "18:00", "19:00", "20:30"
];

// 超时设置
config.timeout = {
    appLaunch: 10000,       // APP启动超时
    pageLoad: 5000,         // 页面加载超时
    upload: 30000,          // 图片上传超时
};

module.exports = config;
