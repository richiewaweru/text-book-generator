import { Popover as PopoverPrimitive } from 'bits-ui';
declare const Root: import("svelte").Component<import("bits-ui").PopoverRootPropsWithoutHTML, {}, "open">;
declare const Trigger: import("svelte").Component<PopoverPrimitive.TriggerProps, {}, "ref">;
declare const Content: import("svelte").Component<PopoverPrimitive.ContentProps, {}, "ref">;
export { Root, Root as Popover, Trigger, Trigger as PopoverTrigger, Content, Content as PopoverContent, };
