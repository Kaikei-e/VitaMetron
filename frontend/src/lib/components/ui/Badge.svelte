<script lang="ts">
	let { text, variant = 'default' }: { text: string; variant?: 'default' | 'success' | 'warning' | 'error' } = $props();

	const variantClasses: Record<string, string> = {
		default: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200',
		success: 'bg-green-100 text-green-700 dark:bg-green-800 dark:text-green-200',
		warning: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-800 dark:text-yellow-200',
		error: 'bg-red-100 text-red-700 dark:bg-red-800 dark:text-red-200'
	};
</script>

<span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {variantClasses[variant]}">
	{text}
</span>
