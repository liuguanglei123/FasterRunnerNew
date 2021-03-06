"""FasterRunner URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from fastrunner.views import project, api, config, schedule, database, run, suite, report,testsuite, newrun, testcase

urlpatterns = [
    # 项目相关接口地址
    path('project/', project.ProjectView.as_view({
        "get": "list",
        "post": "add",
        "patch": "update",
        "delete": "delete"
    })),
    path('project/<int:pk>/', project.ProjectView.as_view({"get": "single"})),

    # 数据库相关接口地址
    # 定时任务相关接口
    path('schedule/', schedule.ScheduleView.as_view({
        "get": "list",
        "post": "add",
    })),

    path('schedule/<int:pk>/', schedule.ScheduleView.as_view({
        "delete": "delete"
    })),

    # debugtalk.py相关接口地址
    path('debugtalk/<int:pk>/', project.DebugTalkView.as_view({"get": "debugtalk"})),
    path('debugtalk/', project.DebugTalkView.as_view({
        "patch": "update",
        "post": "run"
    })),

    # 二叉树接口地址
    path('tree/<int:pk>/', project.TreeView.as_view()),

    # 文件上传 修改 删除接口地址
    path('file/', project.FileView.as_view()),

    # api接口模板地址
    path('api/', api.APITemplateView.as_view({
        "post": "add",
        "get": "list"
    })),

    path('api/<int:pk>/', api.APITemplateView.as_view({
        "delete": "delete",
        "get": "single",
        "patch": "update",
        "post": "copy"
    })),

    # test接口地址
    path('test/', suite.TestCaseView.as_view({
        "get": "get",
        "post": "post",
        "delete": "delete"
    })),

    path('test/<int:pk>/', suite.TestCaseView.as_view({
        "delete": "delete",
        "post": "copy"
    })),

    path('teststep/<int:pk>/', suite.CaseStepView.as_view()),

    # config接口地址
    path('config/', config.ConfigView.as_view({
        "post": "add",
        "get": "list",
        "delete": "delete"
    })),

    path('config/<int:pk>/', config.ConfigView.as_view({
        "post": "copy",
        "delete": "delete",
        "patch": "update",
        "get": "all"
    })),

    path('variables/', config.VariablesView.as_view({
        "post": "add",
        "get": "list",
        "delete": "delete"
    })),

    path('variables/<int:pk>/', config.VariablesView.as_view({
        "delete": "delete",
        "patch": "update"
    })),

    # run api




    # run testsuite
    path('run_testsuite/', run.run_testsuite),
    path('run_test/', run.run_test),
    path('run_testsuite_pk/<int:pk>/', run.run_testsuite_pk),
    path('run_suite_tree/', run.run_suite_tree),

    # 报告地址
    path('reports/', report.ReportView.as_view({
        "get": "list"
    })),

    path('reports/<int:pk>/', report.ReportView.as_view({
        "delete": "delete",
        "get": "look"
    })),

    path('suite/', testsuite.SuiteTemplateView.as_view({
        "post": "add",
        "get": "list"
    })),
    path('suite/<int:pk>/', testsuite.SuiteTemplateView.as_view({
        "patch": "update",
    })),

    path('suitestep/', testsuite.SuiteTemplateView.as_view({
        "get": "getSingleStep",
        "delete": "delete",
        "patch": "updateSingleStep"
    })),

    path('run_suitestep/', newrun.run_suitestep),
    path('run_suitesinglestep/', newrun.run_suitesinglestep),

    path('run_api_pk/<int:pk>/', newrun.run_api_pk),
    path('run_api_tree/', newrun.run_api_tree),
    path('run_api/', newrun.run_api),

    path('testCaseList/', testcase.TestCaseTemplateView.as_view({
        "post": "add",
        "get": "list"
    })),
    path('testCaseList/<int:pk>/', testcase.TestCaseTemplateView.as_view({
        "patch": "update",
    })),
    path('testCaseStep/', testcase.TestCaseTemplateView.as_view({
        "get": "getSingleStep",
        "delete": "delete",
        "patch": "updateSingleStep"
    })),

    path('run_casestep/', newrun.run_casestep),
    path('run_casesinglestep/', newrun.run_casesinglestep),
    path('run_DebugSuiteStep/', newrun.run_DebugSuiteStep),
    path('run_DebugCaseStep/', newrun.run_DebugCaseStep),

    path('host_ip/', config.HostIPView.as_view({
        "post": "add",
        "get": "list"
    })),

    path('host_ip/<int:pk>/', config.HostIPView.as_view({
        "delete": "delete",
        "patch": "update",
        "get": "all"
    })),
]
