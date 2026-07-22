import { defineStore } from 'pinia'

/** @typedef {'feixun' | 'pet' | 'user'} AppToolMenuSection */
/** @typedef {{ top: number, left: number, height: number }} ToolMenuAnchor */

/** @type {HTMLElement | null} */
let anchorElement = null

/** @type {Record<AppToolMenuSection, ToolMenuAnchor>} */
const emptyAnchors = () => ({
  feixun: { top: 0, left: 0, height: 0 },
  pet: { top: 0, left: 0, height: 0 },
  user: { top: 0, left: 0, height: 0 },
})

export const useAppToolMenuStore = defineStore('appToolMenu', {
  state: () => ({
    /** @type {AppToolMenuSection | null} */
    activeSection: null,
    /** @type {Record<AppToolMenuSection, ToolMenuAnchor>} */
    anchors: emptyAnchors(),
  }),

  actions: {
    /**
     * @param {AppToolMenuSection} section
     * @param {HTMLElement | null | undefined} el
     */
    setAnchor(section, el) {
      if (!el) return
      const rect = el.getBoundingClientRect()
      this.anchors[section] = {
        top: rect.top,
        left: rect.right,
        height: rect.height,
      }
    },

    /**
     * @param {AppToolMenuSection} section
     * @param {HTMLElement | null | undefined} el
     */
    toggleSection(section, el) {
      if (this.activeSection === section) {
        this.activeSection = null
        anchorElement = null
        return
      }

      anchorElement = el ?? null
      this.setAnchor(section, el)
      this.activeSection = section
    },

    updateAnchorRect() {
      if (!anchorElement || !this.activeSection) return
      this.setAnchor(this.activeSection, anchorElement)
    },
  },
})
