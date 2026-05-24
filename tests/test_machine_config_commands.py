from __future__ import annotations

from cls_cli.cli import app


def test_machine_group_add_info_invokes_official_action(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        [
            "machine-group",
            "add-info",
            "--region",
            "ap-guangzhou",
            "--group-id",
            "group-123",
            "--ips",
            "10.0.0.1,10.0.0.2",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "AddMachineGroupInfo",
            {
                "GroupId": "group-123",
                "MachineGroupType": {"Type": "ip", "Values": ["10.0.0.1", "10.0.0.2"]},
            },
            "ap-guangzhou",
        )
    ]


def test_config_apply_invokes_binding_action(runner, cli_obj, fake_client):
    result = runner.invoke(
        app,
        [
            "config",
            "apply",
            "--region",
            "ap-guangzhou",
            "--config-id",
            "config-123",
            "--group-id",
            "group-123",
        ],
        obj=cli_obj,
    )

    assert result.exit_code == 0, result.stdout
    assert fake_client.calls == [
        (
            "ApplyConfigToMachineGroup",
            {"ConfigId": "config-123", "GroupId": "group-123"},
            "ap-guangzhou",
        )
    ]
