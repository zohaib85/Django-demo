import sys
import traceback
from datetime import datetime, timezone

def main():
    try:
        # === Get approved tags ===
        tags = get_tags()
        approved_tags = [tag.key for tag in tags]
        print("Approved Tags:", approved_tags)

        # === Parse JSON event ===
        raw_json = sys.argv
        event = parse_cloudevents(raw_json)
        data = event.get('data', {})

        resource_id = get_resource_id(data)
        print("Resource ID:", resource_id)

        upn = get_creator_id(data)
        print("UPN:", upn)

        subscription_id = event.get('source', '').split("/")[-1]
        environment = get_environment(subscription_id)
        print("Environment:", environment)

        # === Get resource tags ===
        client, tags = get_resource_tags(resource_id)
        if client is None or tags is None:
            print(f"[ERROR] No tags found for {resource_id}. Skipping.")
            return

        # === Add time_created tag if missing ===
        if "time_created" not in tags:
            utc_now = datetime.now(timezone.utc)
            formatted_time = utc_now.strftime("%m/%d/%Y %H:%M:%S UTC")
            tags["time_created"] = formatted_time

        # === Check for CI tag ===
        ci_value = tags.get("syf:application:ci")
        if not ci_value:
            print(f"[WARNING] No CI tag found on {resource_id}. Skipping.")
            return

        print("CI tag found:", ci_value)

        # === Fetch CI metadata ===
        try:
            ci_metadata = get_ci_metadata(ci_value)
            print("CI metadata:", ci_metadata)
        except Exception as e:
            print(f"[ERROR] Failed to fetch CI metadata for {ci_value}: {e}")
            return

        # === Add environment if approved ===
        if "syf:environment" in approved_tags:
            ci_metadata["syf:environment"] = environment

        # === Add creator if approved ===
        if upn and "syf:creator.sso" in approved_tags:
            ci_metadata["syf:creator.sso"] = upn

        # === Validate fetched metadata ===
        for key in list(ci_metadata.keys()):
            if key not in approved_tags:
                print("[WARNING] NOT approved:", key)
                ci_metadata.pop(key)

        # === Validate existing tags ===
        for key in list(tags.keys()):
            if key.startswith("syf:") and key not in approved_tags:
                print("[WARNING] Existing NOT approved:", key)
                tags.pop(key)

        # === Merge & update ===
        new_tags = {**tags, **ci_metadata}
        print("NEW tags:", new_tags)

        update_resource_tags(resource_id, new_tags)

    except Exception as e:
        print(f"[FATAL] Unexpected error in main(): {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
