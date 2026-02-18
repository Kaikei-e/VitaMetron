<script lang="ts">
	import ConditionList from '$lib/components/condition/ConditionList.svelte';
	import WHO5Card from '$lib/components/condition/WHO5Card.svelte';
	import DivergenceCard from '$lib/components/condition/DivergenceCard.svelte';
	import DivergenceTimeline from '$lib/components/condition/DivergenceTimeline.svelte';
	import DivergenceDrivers from '$lib/components/condition/DivergenceDrivers.svelte';
	import SkeletonCard from '$lib/components/ui/SkeletonCard.svelte';
	import { filterValidDivergences } from '$lib/utils/divergence';
	import { deleteCondition } from '$lib/api/conditions';
	import { invalidateAll } from '$app/navigation';

	let { data } = $props();

	async function handleDelete(id: number) {
		await deleteCondition(id);
		await invalidateAll();
	}

	let latestDetection = $derived.by(() => {
		const valid = filterValidDivergences(data.divergenceRange ?? []);
		return valid.length > 0 ? valid[valid.length - 1] : null;
	});
</script>

<svelte:head>
	<title>Conditions — VitaMetron</title>
</svelte:head>

<div class="flex items-center justify-between mb-6">
	<h1 class="text-2xl font-bold">Condition Logs</h1>
	<a
		href="/conditions/new"
		class="hidden lg:inline-flex min-h-12 items-center rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
	>
		New Entry
	</a>
</div>

<!-- WHO-5 Card -->
<section class="mb-6">
	<WHO5Card latest={data.who5Latest} />
</section>

{#await data.divergenceStatus}
	<section class="mb-6">
		<SkeletonCard />
	</section>
{:then divergenceStatus}
	{#if divergenceStatus}
		<section class="mb-6 flex flex-col gap-4">
			<DivergenceCard status={divergenceStatus} latest={latestDetection} />

			{#if data.divergenceRange && data.divergenceRange.length > 0}
				<DivergenceTimeline detections={data.divergenceRange} />

				{#if latestDetection?.TopDrivers && latestDetection.TopDrivers.length > 0}
					<DivergenceDrivers drivers={latestDetection.TopDrivers} />
				{/if}
			{/if}
		</section>
	{/if}
{/await}

<ConditionList
	conditions={data.conditions}
	total={data.total}
	page={data.page}
	limit={data.limit}
	ondelete={handleDelete}
/>
