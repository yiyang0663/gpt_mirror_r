import {
  AnalyticsIcon,
  ApiIcon,
  ChartIcon,
  DashboardIcon,
  DataDisplayIcon,
  InternetIcon,
  SecuredIcon,
  UsergroupIcon,
} from 'tdesign-icons-vue-next';

import Layout from '@/layouts/index.vue';

export default [
  {
    path: '/overview-shell',
    component: Layout,
    redirect: '/overview',
    name: 'OverviewShell',
    meta: {
      title: {
        zh_CN: '后台总览',
        en_US: 'Overview',
      },
      icon: DashboardIcon,
      orderNo: 0,
      single: true,
    },
    children: [
      {
        path: '/overview',
        name: 'AdminOverview',
        component: () => import('@/pages/admin/overview.vue'),
        meta: {
          title: {
            zh_CN: '后台总览',
            en_US: 'Overview',
          },
        },
      },
    ],
  },
  {
    path: '/resource-center',
    component: Layout,
    redirect: '/account/chatgpt',
    name: 'ResourceCenter',
    meta: {
      title: {
        zh_CN: '上游与资源',
        en_US: 'Resources',
      },
      icon: InternetIcon,
      orderNo: 1,
    },
    children: [
      {
        path: '/account/chatgpt',
        name: 'ChatGPT',
        component: () => import('@/pages/account/chatgpt.vue'),
        meta: {
          title: {
            zh_CN: '上游账号',
            en_US: 'Accounts',
          },
          icon: ApiIcon,
        },
      },
      {
        path: '/account/gptcar',
        name: 'GPTCar',
        component: () => import('@/pages/account/gptcar.vue'),
        meta: {
          title: {
            zh_CN: '账号池',
            en_US: 'Pools',
          },
          icon: DataDisplayIcon,
        },
      },
    ],
  },
  {
    path: '/customer-center',
    component: Layout,
    redirect: '/account/user',
    name: 'CustomerCenter',
    meta: {
      title: {
        zh_CN: '用户与订阅',
        en_US: 'Customers',
      },
      icon: UsergroupIcon,
      orderNo: 2,
    },
    children: [
      {
        path: '/account/user',
        name: 'User',
        component: () => import('@/pages/account/user.vue'),
        meta: {
          title: {
            zh_CN: '用户',
            en_US: 'Users',
          },
          icon: UsergroupIcon,
        },
      },
      {
        path: '/account/plan',
        name: 'Plan',
        component: () => import('@/pages/account/plan.vue'),
        meta: {
          title: {
            zh_CN: '套餐',
            en_US: 'Plans',
          },
          icon: SecuredIcon,
        },
      },
      {
        path: '/invite',
        name: 'Invite',
        component: () => import('@/pages/account/invite.vue'),
        meta: {
          title: {
            zh_CN: '邀请链接',
            en_US: 'Invites',
          },
          icon: AnalyticsIcon,
        },
      },
    ],
  },
  {
    path: '/observability-center',
    component: Layout,
    redirect: '/system/usage',
    name: 'ObservabilityCenter',
    meta: {
      title: {
        zh_CN: '监控与审计',
        en_US: 'Observability',
      },
      icon: ChartIcon,
      orderNo: 3,
    },
    children: [
      {
        path: '/system/usage',
        name: 'UsageLedger',
        component: () => import('@/pages/system/usage.vue'),
        meta: {
          title: {
            zh_CN: '用量账本',
            en_US: 'Usage Ledger',
          },
          icon: ChartIcon,
        },
      },
      {
        path: '/system/web-usage-sync',
        name: 'WebUsageSync',
        component: () => import('@/pages/system/web_usage_sync.vue'),
        meta: {
          title: {
            zh_CN: '网页用量同步',
            en_US: 'Web Usage Sync',
          },
          icon: DataDisplayIcon,
        },
      },
      {
        path: '/system/login-log',
        name: 'LoginLog',
        component: () => import('@/pages/system/loginlog.vue'),
        meta: {
          title: {
            zh_CN: '登录日志',
            en_US: 'Login Log',
          },
          icon: AnalyticsIcon,
        },
      },
    ],
  },
];
