/**
 * Provide print mode to child components via context.
 * Pass a getter so the value stays reactive.
 * Called by consuming application or the component showcase.
 */
export declare function providePrintMode(getter: () => boolean): void;
/**
 * Read print mode from context.
 * Returns a getter — use inside $derived() for reactivity:
 *   const getPrintMode = usePrintMode();
 *   const printMode = $derived(getPrintMode());
 */
export declare function usePrintMode(): () => boolean;
