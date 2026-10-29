// The "People With Access" list on the Branch form: who has been given this site, with buttons to
// give or remove access. The work is done by krl_hse.utils.branch, which checks the user may edit
// the branch.
frappe.ui.form.on("Branch", {
	refresh(frm) {
		render_people_with_access(frm);
	},
});

function render_people_with_access(frm) {
	const field = frm.fields_dict.hse_users_html;
	if (!field) return;
	const $wrapper = field.$wrapper.empty();

	if (frm.is_new()) {
		$wrapper.html(`<p class="text-muted">${__("Save the branch first, then give people access here.")}</p>`);
		return;
	}
	if (!frappe.model.can_write("Branch")) return;

	frappe.call({
		method: "krl_hse.utils.branch.get_branch_users",
		args: { branch: frm.doc.name },
		callback: (r) => draw(frm, $wrapper, r.message || []),
	});
}

function draw(frm, $wrapper, people) {
	const esc = frappe.utils.escape_html;
	const rows = people
		.map(
			(p) => `<tr>
				<td>${esc(p.full_name || p.user)}${p.enabled ? "" : ` <span class="text-muted">(${__("disabled")})</span>`}</td>
				<td>${esc(p.user)}</td>
				<td>${esc(p.roles.join(", "))}</td>
				<td class="text-right"><button class="btn btn-xs btn-default" data-remove="${esc(p.user)}">${__("Remove")}</button></td>
			</tr>`
		)
		.join("");

	$wrapper.html(`
		<p class="text-muted small">${__("People whose role sees every branch (set in HSE Settings) are not listed here.")}</p>
		<table class="table table-bordered table-sm">
			<thead><tr><th>${__("Name")}</th><th>${__("User")}</th><th>${__("HSE Roles")}</th><th></th></tr></thead>
			<tbody>${rows || `<tr><td colspan="4" class="text-muted">${__("Nobody has been given this site yet.")}</td></tr>`}</tbody>
		</table>
		<button class="btn btn-xs btn-default" data-give>${__("Give Access")}</button>
	`);

	$wrapper.find("[data-give]").on("click", () => {
		frappe.prompt(
			{
				fieldname: "user",
				label: __("User"),
				fieldtype: "Link",
				options: "User",
				reqd: 1,
				get_query: () => ({ filters: { enabled: 1, user_type: "System User" } }),
			},
			(values) => call_and_refresh(frm, "grant_branch_access", values.user),
			__("Give access to {0}", [frm.doc.name]),
			__("Give Access")
		);
	});

	$wrapper.find("[data-remove]").on("click", (e) => {
		const user = $(e.currentTarget).attr("data-remove");
		frappe.confirm(__("Take {0} away from {1}?", [frm.doc.name, user]), () =>
			call_and_refresh(frm, "revoke_branch_access", user)
		);
	});
}

function call_and_refresh(frm, method, user) {
	frappe.call({
		method: `krl_hse.utils.branch.${method}`,
		args: { branch: frm.doc.name, user },
		callback: () => render_people_with_access(frm),
	});
}
