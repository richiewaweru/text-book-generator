import type { TemplateContract, TemplatePresetDefinition } from '../template-types';
type $$ComponentProps = {
    contract: TemplateContract;
    presets: TemplatePresetDefinition[];
    desktopOpen?: boolean;
    isDesktop?: boolean;
};
declare const TemplateContractDrawer: import("svelte").Component<$$ComponentProps, {}, "desktopOpen" | "isDesktop">;
type TemplateContractDrawer = ReturnType<typeof TemplateContractDrawer>;
export default TemplateContractDrawer;
