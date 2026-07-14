import { defineStore } from 'pinia'

/** @typedef {{ id?: string, label: string, icon?: string, disabled?: boolean, danger?: boolean, action?: () => void }} PhroContextMenuItem */

export const usePhroContextMenuStore = defineStore('phroContextMenu', {
  state: () => ({
    visible: false,
    x: 0,
    y: 0,
    /** @type {PhroContextMenuItem[]} */
    items: [],
  }),

  actions: {
    /** @param {{ x: number, y: number, items: PhroContextMenuItem[] }} payload */
    open(payload) {
      this.x = payload.x
      this.y = payload.y
      this.items = payload.items
      this.visible = true
    },

    close() {
      this.visible = false
    },

    clearContent() {
      this.items = []
    },

    /** @param {PhroContextMenuItem} item */
    runItem(item) {
      if (item.disabled) return
      item.action?.()
      this.close()
    },
  },
})
