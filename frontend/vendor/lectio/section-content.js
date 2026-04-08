export function getSectionSimulations(section) {
    if (section.simulations?.length) {
        return section.simulations;
    }
    return section.simulation ? [section.simulation] : [];
}
