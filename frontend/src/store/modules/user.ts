import Cookies from 'js-cookie';
import { defineStore } from 'pinia';
import { MessagePlugin } from 'tdesign-vue-next';

import { usePermissionStore } from '@/store';
import type { UserInfo } from '@/types/interface';

const InitUserInfo: UserInfo = {
  name: '', // 用户名，用于展示在页面右上角头像处
  roles: [], // 前端权限模型使用 如果使用请配置modules/permission-fe.ts使用
};

const TOKEN_COOKIE_KEY = 'user_token';
const ADMIN_COOKIE_KEY = 'user_is_admin';

const readTokenCookie = () => Cookies.get(TOKEN_COOKIE_KEY) || '';

const readAdminCookie = () => Cookies.get(ADMIN_COOKIE_KEY) === '1';

export const useUserStore = defineStore('user', {
  state: () => ({
    token: readTokenCookie(),
    is_admin: readAdminCookie(),
    userInfo: { ...InitUserInfo },
  }),
  getters: {
    roles: (state) => {
      return state.userInfo?.roles;
    },
  },
  actions: {
    hydrateAuthState() {
      const cookieToken = readTokenCookie();
      if (!this.token && cookieToken) {
        this.token = cookieToken;
      }

      if (!this.is_admin && readAdminCookie()) {
        this.is_admin = true;
      }
    },

    async login(url: string, userInfo: Record<string, unknown>) {
      const response = await fetch(url, {
        method: 'POST',
        body: JSON.stringify(userInfo),
        headers: {
          'Content-Type': 'application/json',
        },
      });
      let data = null;
      if (response.status === 200) {
        data = await response.json();
        this.token = data.admin_token;
        this.is_admin = data.is_admin === true;
        Cookies.set(TOKEN_COOKIE_KEY, data.admin_token, { expires: 7, path: '/' });
        Cookies.set(ADMIN_COOKIE_KEY, this.is_admin ? '1' : '0', { expires: 7, path: '/' });
        MessagePlugin.success('登录成功');
      } else if (response.status === 400) {
        data = await response.json();
        MessagePlugin.error(JSON.stringify(Object.values(data)[0]));
      } else if (response.status === 502) {
        MessagePlugin.error('服务未正常启动');
        return new Response();
      } else if (response.status === 500) {
        MessagePlugin.error('系统异常，请稍后再试');
      }
      return data;
    },

    async logout() {
      const permissionStore = usePermissionStore();
      this.token = '';
      this.is_admin = false;
      this.userInfo = { ...InitUserInfo };
      Cookies.remove(TOKEN_COOKIE_KEY, { path: '/' });
      Cookies.remove(ADMIN_COOKIE_KEY, { path: '/' });
      await permissionStore.restoreRoutes();
    },
  },
  persist: {
    afterRestore: (context) => {
      const userStore = context.store as ReturnType<typeof useUserStore>;
      userStore.hydrateAuthState();
      const permissionStore = usePermissionStore();
      permissionStore.initRoutes();
    },
    key: 'user',
    paths: ['token', 'is_admin'],
  },
});
