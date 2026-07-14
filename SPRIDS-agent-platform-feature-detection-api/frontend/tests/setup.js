/**
 * Vitest 全局 setup
 * 在每个测试⽂件执⾏前⾃动运⾏
 */
import { vi } from "vitest";
vi.mock("element-plus", async () => {
  const actual = await vi.importActual("element-plus");
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
    ElMessageBox: {
      confirm: vi.fn().mockResolvedValue(true),
    },
  };
});
vi.mock("@element-plus/icons-vue", async () => {
  const actual = await vi.importActual("@element-plus/icons-vue");
  const mocks = {};
  for (const key of Object.keys(actual)) {
    mocks[key] = vi.fn();
  }
  return mocks;
});