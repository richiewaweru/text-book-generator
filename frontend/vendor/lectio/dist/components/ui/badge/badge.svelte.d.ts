import type { Snippet } from 'svelte';
import type { HTMLAttributes } from 'svelte/elements';
import type { BadgeVariant } from './index.js';
interface Props extends HTMLAttributes<HTMLDivElement> {
    variant?: BadgeVariant;
    children?: Snippet;
    class?: string;
}
declare const Badge: import("svelte").Component<Props, {}, "">;
type Badge = ReturnType<typeof Badge>;
export default Badge;
