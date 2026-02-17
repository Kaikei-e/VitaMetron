<script lang="ts">
	let { text, variant = 'default' }: { text: string; variant?: 'default' | 'success' | 'warning' | 'error' } = $props();

	const variantClasses: Record<string, string> = {
		default: 'bg-gray-100 text-gray-700',
		success: 'bg-green-100 text-green-700',
		warning: 'bg-yellow-100 text-yellow-700',
		error: 'bg-red-100 text-red-700'
	};
</script>

<span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {variantClasses[variant]}">
	{text}
</span>
