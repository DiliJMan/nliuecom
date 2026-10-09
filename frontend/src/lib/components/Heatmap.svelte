<script lang="ts">
	type Level = { name: string; colour: string };
	type Matrix = { probability: { name: string }[]; impact: { name: string }[]; levels: Level[]; grid: number[][] };

	let { matrix, counts, title }: { matrix: Matrix; counts: number[][]; title: string } = $props();

	// Light text on dark cells and the reverse, chosen from the cell colour's luminance.
	function ink(hex: string): string {
		const n = parseInt(hex.slice(1), 16);
		const luminance = (0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255;
		return luminance > 0.55 ? '#1c2330' : '#ffffff';
	}
	// Highest likelihood at the top, as risk matrices are normally drawn.
	const rows = $derived([...matrix.probability.keys()].reverse());
</script>

<figure style="margin: 0">
	<figcaption style="font-weight: 600; margin-bottom: 6px">{title}</figcaption>
	<table class="heat" aria-label={title}>
		<thead>
			<tr><th></th>{#each matrix.impact as impact (impact.name)}<th scope="col">{impact.name}</th>{/each}</tr>
		</thead>
		<tbody>
			{#each rows as p (p)}
				<tr>
					<th scope="row">{matrix.probability[p].name}</th>
					{#each matrix.impact as _, i (i)}
						{@const level = matrix.levels[matrix.grid[p][i]]}
						<td style="background: {level.colour}; color: {ink(level.colour)}" title="{level.name}: {counts[p][i]} scenario(s)">
							{counts[p][i] || ''}
							<span class="sr-only">{level.name}, {counts[p][i]} scenarios</span>
						</td>
					{/each}
				</tr>
			{/each}
		</tbody>
	</table>
	<div class="legend">
		{#each matrix.levels as level (level.name)}
			<span><i style="background: {level.colour}"></i>{level.name}</span>
		{/each}
	</div>
</figure>

<style>
	.heat { border-collapse: separate; border-spacing: 3px; width: auto; }
	.heat th { border: 0; text-transform: none; letter-spacing: 0; font-size: 0.75rem; padding: 2px 6px; }
	.heat td { border: 0; width: 64px; height: 40px; text-align: center; font-weight: 700; border-radius: 4px; padding: 0; vertical-align: middle; }
	.legend { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 8px; font-size: 0.8rem; }
	.legend i { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 4px; vertical-align: -1px; }
</style>
