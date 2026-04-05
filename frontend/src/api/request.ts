// eslint-disable-next-line simple-import-sort/imports
import { MessagePlugin } from 'tdesign-vue-next';

import router from '@/router';
import { useUserStore } from '@/store';

const RequestApi = async (url: string, method = 'GET', body: any = undefined) => {
  const userStore = useUserStore();
  userStore.hydrateAuthState();
  const { token } = userStore;
  const defaultHeaders = {
    'Content-Type': 'application/json',
    Authorization: `Token ${token}`,
  };

  const response = await fetch(url, {
    method,
    headers: defaultHeaders,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401) {
    await userStore.logout();
    router.push({
      path: '/login',
      query: { redirect: encodeURIComponent(router.currentRoute.value.fullPath) },
    });
    return new Response();
  }

  if (response.status === 403) {
    await userStore.logout();
    router.push({
      path: '/login',
      query: { redirect: encodeURIComponent(router.currentRoute.value.fullPath) },
    });
    return new Response();
  }

  if (response.status === 500) {
    MessagePlugin.error('系统异常');
    return new Response();
  }

  if (response.status === 502) {
    MessagePlugin.error('服务未正常启动');
    return new Response();
  }

  return response;
};

export default RequestApi;
