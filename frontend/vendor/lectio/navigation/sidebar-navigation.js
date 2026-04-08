import { getStableComponents } from '../registry';
import { templateRegistry } from '../template-registry';
export function getSidebarNavigation() {
    return {
        components: getStableComponents().map((component) => ({
            href: `/components#${component.id}`,
            label: component.name,
            meta: `Group ${component.group} - ${component.cognitiveJob}`
        })),
        templates: [
            {
                href: '/templates',
                label: 'Template gallery',
                meta: `${templateRegistry.length} starter templates`
            },
            ...templateRegistry.map(({ contract }) => ({
                href: `/templates/${contract.id}`,
                label: contract.name,
                meta: contract.family
            }))
        ]
    };
}
