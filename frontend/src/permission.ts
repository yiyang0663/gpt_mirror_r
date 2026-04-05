import 'nprogress/nprogress.css'; // progress bar style

import NProgress from 'nprogress'; // progress bar
import { MessagePlugin } from 'tdesign-vue-next';
import { RouteRecordRaw } from 'vue-router';

import router from '@/router';
import { getPermissionStore, useUserStore } from '@/store';
import { PAGE_NOT_FOUND_ROUTE } from '@/utils/route/constant';

NProgress.configure({ showSpinner: false });

router.beforeEach(async (to, from, next) => {
  NProgress.start();

  const permissionStore = getPermissionStore();
  const { whiteListRouters } = permissionStore;

  const userStore = useUserStore();
  const isAuthEntryRoute = ['/login', '/register', '/invite_register'].includes(to.path);
  const authenticatedHomePath = userStore.is_admin ? '/account/user' : '/customer/chat';

  if (userStore.token) {
    if (isAuthEntryRoute) {
      const redirectQuery = typeof to.query.redirect === 'string' ? decodeURIComponent(to.query.redirect) : '';
      const nextPath =
        redirectQuery && !['/login', '/register', '/invite_register'].includes(redirectQuery)
          ? redirectQuery
          : authenticatedHomePath;

      next({ path: nextPath, replace: true });
      NProgress.done();
      return;
    }
    try {
      // await userStore.getUserInfo();

      const { asyncRoutes } = permissionStore;

      if (asyncRoutes && asyncRoutes.length === 0) {
        const routeList = await permissionStore.buildAsyncRoutes();
        routeList.forEach((item: RouteRecordRaw) => {
          router.addRoute(item);
        });

        if (to.name === PAGE_NOT_FOUND_ROUTE.name) {
          // 动态添加路由后，此处应当重定向到fullPath，否则会加载404页面内容
          next({ path: to.fullPath, replace: true, query: to.query });
        } else {
          let redirect;
          if (to.path !== '/login-chatgpt') {
            redirect = from.query?.redirect;
          }
          redirect = decodeURIComponent((redirect || to.path) as string);
          // console.log('redirect', redirect);
          next(to.path === redirect ? { ...to, replace: true } : { path: redirect, query: to.query });
          return;
        }
      }
      if (router.hasRoute(to.name)) {
        next();
      } else {
        next(`/`);
      }
    } catch (error) {
      MessagePlugin.error(error.message);
      next({
        path: '/login',
        query: { redirect: encodeURIComponent(to.fullPath) },
      });
      NProgress.done();
    }
  } else {
    /* white list router */
    if (whiteListRouters.indexOf(to.path) !== -1) {
      next();
    } else {
      next({
        path: '/login',
        query: { redirect: encodeURIComponent(to.fullPath) },
      });
    }
    NProgress.done();
  }
});

router.afterEach(() => {
  NProgress.done();
});
