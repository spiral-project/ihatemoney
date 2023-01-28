from sqlalchemy_continuum import Operation, parent_class

from ihatemoney.models import BillVersion, Person, PersonVersion, ProjectVersion


def get_history_queries(project):
    """Generate queries for each type of version object for a given project."""
    person_changes = PersonVersion.query.filter_by(project_id=project.id)

    project_changes = ProjectVersion.query.filter_by(id=project.id)

    bill_changes = (
        BillVersion.query.with_entities(BillVersion.id.label("bill_version_id"))
        .join(Person, BillVersion.payer_id == Person.id)
        .filter(Person.project_id == project.id)
    )
    sub_query = bill_changes.subquery()
    bill_changes = BillVersion.query.filter(BillVersion.id.in_(sub_query))

    return person_changes, project_changes, bill_changes


def history_sort_key(history_item_dict):
    """
    Return the key necessary to sort history entries. First order sort is time
    of modification, but for simultaneous modifications we make the re-name
    modification occur last so that the simultaneous entries make sense using
    the old name.
    """
    second_order = 0
    if "prop_changed" in history_item_dict:
        changed_property = history_item_dict["prop_changed"]
        if changed_property == "name" or changed_property == "what":
            second_order = 1

    return history_item_dict["time"], second_order


def describe_version(version_obj):
    """Use the base model str() function to describe a version object"""
    return parent_class(type(version_obj)).__str__(version_obj)


def describe_owers_change(version, human_readable_names):
    """Compute the set difference to get added/removed owers lists."""
    before_owers = {version.id: version for version in version.previous.owers}
    after_owers = {version.id: version for version in version.owers}

    added_ids = set(after_owers).difference(set(before_owers))
    removed_ids = set(before_owers).difference(set(after_owers))

    if not human_readable_names:
        return added_ids, removed_ids

    added = [describe_version(after_owers[ower_id]) for ower_id in added_ids]
    removed = [describe_version(before_owers[ower_id]) for ower_id in removed_ids]

    return added, removed


def get_history(project, human_readable_names=True):
    """
    Fetch history for all models associated with a given project.
    :param human_readable_names Whether to replace id numbers with readable names
    :return A sorted list of dicts with history information
    """
    person_query, project_query, bill_query = get_history_queries(project)
    history = []
    for version_list in [person_query.all(), project_query.all(), bill_query.all()]:
        for version in version_list:
            object_type = parent_class(type(version)).__name__

            # The history.html template can only handle objects of these types
            assert object_type in ["Person", "Bill", "Project"]

            # Use the old name if applicable
            if version.previous:
                object_str = describe_version(version.previous)
            else:
                object_str = describe_version(version)

            common_properties = {
                "time": version.transaction.issued_at,
                "operation_type": version.operation_type,
                "object_type": object_type,
                "object_desc": object_str,
                "ip": version.transaction.remote_addr,
            }

            if version.operation_type == Operation.UPDATE:
                # Only iterate the changeset if the previous version
                # Was logged
                if version.previous:
                    changeset = version.changeset
                    if isinstance(version, BillVersion):
                        if version.owers != version.previous.owers:
                            added, removed = describe_owers_change(
                                version, human_readable_names
                            )

                            if added:
                                changeset["owers_added"] = (None, added)
                            if removed:
                                changeset["owers_removed"] = (None, removed)

                        # Remove converted_amount if amount changed in the same way.
                        if (
                            "amount" in changeset
                            and "converted_amount" in changeset
                            and changeset["amount"] == changeset["converted_amount"]
                        ):
                            del changeset["converted_amount"]

                    for prop, (val_before, val_after) in changeset.items():
                        if human_readable_names:
                            if prop == "payer_id":
                                prop = "payer"
                                if val_after is not None:
                                    val_after = describe_version(version.payer)
                                if version.previous and val_before is not None:
                                    val_before = describe_version(
                                        version.previous.payer
                                    )
                                else:
                                    val_after = None

                        next_event = common_properties.copy()
                        next_event["prop_changed"] = prop
                        next_event["val_before"] = val_before
                        next_event["val_after"] = val_after
                        history.append(next_event)
                else:
                    history.append(common_properties)
            else:
                history.append(common_properties)

    return sorted(history, key=history_sort_key, reverse=True)


def purge_history(project):
    """
    Erase history linked to a project.
    You must commit the purge after calling this function.
    """
    for query in get_history_queries(project):
        query.delete(synchronize_session="fetch")
