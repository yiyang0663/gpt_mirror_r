// eslint-disable-next-line simple-import-sort/imports
import { MessagePlugin } from 'tdesign-vue-next';

import router from '@/router';
import { useUserStore } from '@/store';

const buildErrorResponse = (status: number, message = '') => {
  return new Response(message ? JSON.stringify({ message }) : null, {
    status,
    headers: {
      'Content-Type': 'application/json',
    },
  });
};

const RequestApi = async (url: string, method = 'GET', body: any = undefined) => {
  const userStore = useUserStore();
  userStore.hydrateAuthState();
  const { token } = userStore;
  const defaultHeaders = {
    'Content-Type': 'application/json',
    Authorization: `Token ${token}`,
  };

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: defaultHeaders,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    console.error(error);
    MessagePlugin.error('网络请求失败');
    return buildErrorResponse(503, 'network_error');
  }

  if (response.status === 401) {
    await userStore.logout();
    router.push({
      path: '/login',
      query: { redirect: encodeURIComponent(router.currentRoute.value.fullPath) },
    });
    return buildErrorResponse(401, 'unauthorized');
  }

  if (response.status === 403) {
    await userStore.logout();
    router.push({
      path: '/login',
      query: { redirect: encodeURIComponent(router.currentRoute.value.fullPath) },
    });
    return buildErrorResponse(403, 'forbidden');
  }

  if (response.status === 500) {
    MessagePlugin.error('系统异常');
    return buildErrorResponse(500, 'server_error');
  }

  if (response.status === 502) {
    MessagePlugin.error('服务未正常启动');
    return buildErrorResponse(502, 'bad_gateway');
  }

  return response;
};

export default RequestApi;
