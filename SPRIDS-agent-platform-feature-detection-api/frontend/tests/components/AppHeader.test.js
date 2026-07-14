/**
 * AppHeader 组件测试（示例）
 *
 * 注意：组件测试需要完整模拟 Element Plus 和 Router，
 * Day 4 先测试⼯具函数，组件测试在后续 Day 中完善。
 */
import { describe, it, expect, vi } from "vitest";
vi.mock("@/stores/user", () => ({
  useUserStore: () => ({
    username: "testuser",
    avatar: null,
    logout: vi.fn(),
  }),
}));
vi.mock("vue-router", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));
describe("AppHeader 组件", () => {
  it("组件⽂件应该存在", async () => {
    const { default: AppHeader } = await import("@/components/layout/AppHeader.vue");
    expect(AppHeader).toBeDefined();
  }, 15000);
});