import type { Component } from 'svelte';
type PrimitiveComponent = Component<any>;
declare const Root: PrimitiveComponent;
declare const Trigger: PrimitiveComponent;
declare const Content: PrimitiveComponent;
declare const Provider: PrimitiveComponent;
export { Root, Root as Tooltip, Trigger, Trigger as TooltipTrigger, Content, Content as TooltipContent, Provider, Provider as TooltipProvider, };
