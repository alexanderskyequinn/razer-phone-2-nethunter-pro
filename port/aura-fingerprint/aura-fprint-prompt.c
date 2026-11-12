/* SPDX-License-Identifier: MIT
 * Unprivileged GNOME prompt client. A trusted root broker supplies the private
 * pipe; no secret is printed, placed in arguments or persisted by this client.
 */
#define _GNU_SOURCE
#define GCR_API_SUBJECT_TO_CHANGE
#include <gcr/gcr.h>
#include <gcrypt.h>
#include <glib-unix.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <unistd.h>

static gboolean cancel_prompt(gpointer data)
{
	g_cancellable_cancel(data);
	return G_SOURCE_CONTINUE;
}

int main(int argc, char **argv)
{
	struct rlimit no_core = {0, 0};
	if (!getuid() || getuid() != geteuid() || setrlimit(RLIMIT_CORE, &no_core)) return 1;
	if (prctl(PR_SET_DUMPABLE, 0)) return 1;
	gboolean preview = argc == 2 && !strcmp(argv[1], "--preview");
	int output = -1;
	if (!preview) {
		if (argc != 3 || strcmp(argv[1], "--credential-fd")) return 2;
		char *end;
		errno = 0;
		long value = strtol(argv[2], &end, 10);
		if (errno || *end || value < 3 || value > 1024) return 2;
		output = value;
		struct stat st;
		int flags = fcntl(output, F_GETFL);
		if (flags < 0 || (flags & O_ACCMODE) != O_WRONLY || fstat(output, &st) || !S_ISFIFO(st.st_mode)) return 2;
		if (fcntl(output, F_SETFL, flags | O_NONBLOCK)) return 1;
	}
	if (!gcry_check_version(NULL)) return 1;
	signal(SIGPIPE, SIG_IGN);
	GCancellable *cancel = g_cancellable_new();
	guint term = g_unix_signal_add(SIGTERM, cancel_prompt, cancel);
	guint interrupt = g_unix_signal_add(SIGINT, cancel_prompt, cancel);
	guint timer = g_timeout_add_seconds(120, cancel_prompt, cancel);
	GError *error = NULL;
	GcrPrompt *prompt = gcr_system_prompt_open(10, cancel, &error);
	int result = 1;
	if (!prompt) goto done;
	gcr_prompt_set_title(prompt, "Fingerprint setup");
	gcr_prompt_set_message(prompt, preview ? "Check the standard system dialog" : "Authorize fingerprint enrollment");
	gcr_prompt_set_description(prompt, preview ? "No PIN is requested. Nothing will be enrolled." :
		"Enter your existing fingerprint setup PIN to authorize this enrollment. This does not change your login password.");
	gcr_prompt_set_continue_label(prompt, preview ? "Continue" : "Authorize");
	gcr_prompt_set_cancel_label(prompt, "Cancel");
	if (preview) {
		result = gcr_prompt_confirm_run(prompt, cancel, &error) == GCR_PROMPT_REPLY_CONTINUE ? 0 : 4;
	} else {
		const gchar *secret = gcr_prompt_password_run(prompt, cancel, &error);
		if (!secret || g_cancellable_is_cancelled(cancel)) { result = error && !g_cancellable_is_cancelled(cancel) ? 1 : 4; goto close; }
		/* Owned by GCR. Unref releases it; never make a second string copy. */
		size_t size = strnlen(secret, 65);
		if (size < 4 || size > 64) goto close;
		for (size_t i = 0; i < size; ++i) if (secret[i] < '0' || secret[i] > '9') goto close;
		if (write(output, secret, size) == (ssize_t)size && write(output, "\n", 1) == 1) result = 0;
	}
close:
	gcr_prompt_close(prompt);
	g_object_unref(prompt);
done:
	if (error) { g_error_free(error); if (result != 4) result = 1; }
	if (output >= 0) close(output);
	g_source_remove(timer);
	g_source_remove(interrupt);
	g_source_remove(term);
	g_object_unref(cancel);
	return result;
}
