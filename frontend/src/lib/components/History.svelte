<script lang="ts">
	import type { Schemas } from '#lib/api/client.ts';
	let { events }: { events: Schemas['AuditEvent'][] } = $props();

	const show = (value: unknown) => (value === null || value === undefined || value === '' ? '(empty)' : typeof value === 'object' ? JSON.stringify(value) : String(value));
	const summary = (changes: unknown): [string, unknown][] => Object.entries((changes ?? {}) as Record<string, unknown>);
</script>

{#if events.length === 0}
	<p class="muted">No recorded history.</p>
{:else}
	<table>
		<thead><tr><th>When (UTC)</th><th>Who</th><th>Action</th><th>Detail</th></tr></thead>
		<tbody>
			{#each events as event (event.id)}
				<tr>
					<td class="mono">{event.timestamp.slice(0, 19).replace('T', ' ')}</td>
					<td>{event.actor_email || 'system'}</td>
					<td>{event.action}</td>
					<td>
						{#each summary(event.changes) as [field, change] (field)}
							<div>
								<span class="mono">{field}</span>:
								{#if Array.isArray(change) && change.length === 2}
									<span class="muted">{show(change[0])}</span> → {show(change[1])}
								{:else}
									{show(change)}
								{/if}
							</div>
						{/each}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
{/if}
