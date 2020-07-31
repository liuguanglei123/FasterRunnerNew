# FasterRunner

[![LICENSE](https://img.shields.io/github/license/HttpRunner/FasterRunner.svg)](https://github.com/HttpRunner/FasterRunner/blob/master/LICENSE) [![travis-ci](https://travis-ci.org/HttpRunner/FasterRunner.svg?branch=master)](https://travis-ci.org/HttpRunner/FasterRunner) ![pyversions](https://img.shields.io/pypi/pyversions/Django.svg)

> FasterRunner that depends FasterWeb

```

## Docker 部署 uwsgi+nginx模式
1. docker pull docker.io/mysql:5.7 # 拉取mysql5.7镜像
2. docker run --name mysql --net=host -d --restart always -v /var/lib/mysql:/var/lib/mysql -e  MYSQL_ROOT_PASSWORD=lcc123456 docker.io/mysql:5.7 --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci  # 运行mysql容器
3. 连接数据库, 新建一个db，例如fastrunner
4. 修改settings.py DATABASES 字典相关配置，NAME, USER, PASSWORD, HOST
5. 启动rabbitmq docker run -d --name --net=host --restart always rabbitmq -e RABBITMQ_DEFAULT_USER=user -e RABBITMQ_DEFAULT_PASS=password rabbitmq:3-management
6. 修改settings.py BROKER_URL(配置rabbittmq的IP，username,password)
7. 切换到FasterRunner目录，Linux环境执行下 dos2unix ./start.sh # 因为windos编写的bash有编码问题
8. docker build -t fastrunner:latest .    # 构建docker镜像
9. docker run -d --name fastrunner --net=host --restart always fastrunner:latest  # 后台运行docker容器,默认后台端口5000
10. docker exec -it fastrunner /bin/sh  #进入容器内部
11. 应用数据库表
``` bash

# make migrations for fastuser、fastrunner
python3 manage.py makemigrations fastrunner fastuser

# migrate for database
python3 manage.py migrate fastrunner
python3 manage.py migrate fastuser
python3 manage.py migrate djcelery
```

# 项目起源

	公司当下并没有任何自动化的回归环节，遇到版本发布时，需要手动回归的内容较多，因此尝试建立自动化接口测试，可以在每次版本发布前进行功能回归。
  
为了快速搭建回归环节，公司最终采用了postman管理接口并实现自动化，并未采用本工具。但我感觉postman局限性较多，偶然间得知基于httprunner的FasterRunner工具，可以方便的管理接口api和测试步骤。由于FasterRunner原版更新较慢，且底层的httprunner近半年有大版本升级，为了工具能有更好的体验，便尝试在原版FasterRunner的基础上进行改动，除了保留了作者的设计模式和部分前端样式外，其他内容基本都有做调整或者重写。前端重写部分包括增加前端“步骤集”选项，步骤集和测试用例页面中，增加添加步骤/用例按钮，增加添加步骤对话框并与后台交互。后端重写了api/步骤集和测试用例的新增/更新逻辑，以及最核心的run方法，可以支持httprunner2.0版本的特性。重写过程中尽量采用低耦合方式，简化更新和执行模块之间的依赖关系，方便以后的覆写和升级。

除了继续修复存在的bug和部分功能的支持外，项目后续新的思路和演进方向为：

1.实现案例保存，执行，测试报告解析等模块的完全解耦合

2.实现定时任务的执行

3.步骤集页面中可以嵌套其他步骤集

4.可以像hrun脚本样式案例一样实现config/debugtalk.py多层嵌套

项目github地址：

前端：https://github.com/liuguanglei123/FasterWebNew

后端：https://github.com/liuguanglei123/FasterRunnerNew

主要功能说明：
api模板：
定义单个接口的参数，可以理解为测试步骤中的某一步操作（比如登录）的定义
![11.png](https://github.com/liuguanglei123/httprunnerforjava_public/blob/master/src/test/showphoto/11.png)

单个接口的编辑页面如下图，可以对接口url，method，http消息中的header和body进行编辑，validate选项卡中为接口相应校验内容，extract为输出参数，在多步骤测试案例中，上步输出参数可以为下步输出参数使用，variables中为变量定义，hook为钩子函数，可以指定在步骤执行前/后执行指定代码。

![12.png](https://github.com/liuguanglei123/httprunnerforjava_public/blob/master/src/test/showphoto/12.png)

步骤集：
可以将用例执行过程中顺序操作的部分接口合并为一个步骤集，比如购物过程中从查看商品到下单付款的整个流程，可以减少用例的操作复杂度，也使逻辑更清晰。

![13.png](https://github.com/liuguanglei123/httprunnerforjava_public/blob/master/src/test/showphoto/13.png)

测试用例部分：
可以将上面定义的步骤集和单个步骤，在测试用例中进行组合，比如单独操作登录+步骤集（查看测试题到下单的完整流程）

![14.png](https://github.com/liuguanglei123/httprunnerforjava_public/blob/master/src/test/showphoto/14.png)

测试结果查看
用例执行完成后，可以直接进行查看（不保存），或者采用异步执行的方式，将测试结果保存在数据库后续查看。

![15.png](https://github.com/liuguanglei123/httprunnerforjava_public/blob/master/src/test/showphoto/15.png)

