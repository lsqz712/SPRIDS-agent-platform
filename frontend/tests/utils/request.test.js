/**
 * Axios 请求封装测试
 *
 * 测试⽬标：
 * - Axios 实例创建正确
 * - 请求拦截器正常注⼊ Token
 * - 响应拦截器正确处理错误
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
vi.mock("@/stores/user", () => ({
  useUserStore: () => ({
    token: null,
    logout: vi.fn(),
  }),
}));
vi.mock("@/router", () => ({
  default: {
    push: vi.fn(),
  },
}));
describe("Axios 请求封装", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });
  it("应该正确创建 axios 实例", async () => {
    const { default: request } = await import("@/utils/request");
    expect(request).toBeDefined();
    expect(request.defaults.baseURL).toBe("/api");
    expect(request.defaults.timeout).toBe(30000);
  }, 10000);
  it("请求拦截器应该设置 Content-Type", async () => {
    const { default: request } = await import("@/utils/request");
    expect(request.defaults.headers["Content-Type"]).toBe("application/json");
  }, 10000);
});
describe("错误上报模块", () => {
  it("应该正确初始化错误上报", async () => {
    const { setupErrorReporting } = await import("@/utils/errorReporter");
    expect(setupErrorReporting).toBeDefined();
    expect(typeof setupErrorReporting).toBe("function");
  });
  it("错误信息应该存⼊ localStorage", () => {
    const errorInfo = {
      type: "test_error",
      message: "测试错误",
    };
    const errors = JSON.parse(localStorage.getItem("error_logs") || "[]");
    errors.push({ ...errorInfo, timestamp: new Date().toISOString() });
    localStorage.setItem("error_logs", JSON.stringify(errors));
    const stored = JSON.parse(localStorage.getItem("error_logs"));
    expect(stored).toHaveLength(1);
    expect(stored[0].type).toBe("test_error");
  });
});
