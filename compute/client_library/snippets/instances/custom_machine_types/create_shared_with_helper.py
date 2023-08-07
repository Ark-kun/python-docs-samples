#  Copyright 2022 Google LLC
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# flake8: noqa


# This file is automatically generated. Please do not modify it directly.
# Find the relevant recipe file in the samples/recipes or samples/ingredients
# directory and apply your changes there.


# [START compute_custom_machine_type_create_shared_with_helper]
from __future__ import annotations

from collections import namedtuple
from enum import Enum
from enum import unique
import re
import sys
from typing import Any
import warnings

from google.api_core.extended_operation import ExtendedOperation
from google.cloud import compute_v1


def gb_to_mb(value: int) -> int:
    return value << 10


class CustomMachineType:
    """
    Allows to create custom machine types to be used with the VM instances.
    """

    @unique
    class CPUSeries(Enum):
        N1 = "custom"
        N2 = "n2-custom"
        N2D = "n2d-custom"
        E2 = "e2-custom"
        E2_MICRO = "e2-custom-micro"
        E2_SMALL = "e2-custom-small"
        E2_MEDIUM = "e2-custom-medium"

    TypeLimits = namedtuple(
        "TypeLimits",
        [
            "allowed_cores",
            "min_mem_per_core",
            "max_mem_per_core",
            "allow_extra_memory",
            "extra_memory_limit",
        ],
    )

    # The limits for various CPU types are described on:
    # https://cloud.google.com/compute/docs/general-purpose-machines
    LIMITS = {
        CPUSeries.E2: TypeLimits(frozenset(range(2, 33, 2)), 512, 8192, False, 0),
        CPUSeries.E2_MICRO: TypeLimits(frozenset(), 1024, 2048, False, 0),
        CPUSeries.E2_SMALL: TypeLimits(frozenset(), 2048, 4096, False, 0),
        CPUSeries.E2_MEDIUM: TypeLimits(frozenset(), 4096, 8192, False, 0),
        CPUSeries.N2: TypeLimits(
            frozenset(range(2, 33, 2)).union(set(range(36, 129, 4))),
            512,
            8192,
            True,
            gb_to_mb(624),
        ),
        CPUSeries.N2D: TypeLimits(
            frozenset({2, 4, 8, 16, 32, 48, 64, 80, 96}), 512, 8192, True, gb_to_mb(768)
        ),
        CPUSeries.N1: TypeLimits(
            frozenset({1}.union(range(2, 97, 2))), 922, 6656, True, gb_to_mb(624)
        ),
    }

    def __init__(
        self, zone: str, cpu_series: CPUSeries, memory_mb: int, core_count: int = 0
    ):
        self.zone = zone
        self.cpu_series = cpu_series
        self.limits = self.LIMITS[self.cpu_series]
        # Shared machine types (e2-small, e2-medium and e2-micro) always have
        # 2 vCPUs: https://cloud.google.com/compute/docs/general-purpose-machines#e2_limitations
        self.core_count = 2 if self.is_shared() else core_count
        self.memory_mb = memory_mb
        self._checked = False
        self._check_parameters()
        self.extra_memory_used = self._check_extra_memory()

    def is_shared(self):
        return self.cpu_series in (
            CustomMachineType.CPUSeries.E2_SMALL,
            CustomMachineType.CPUSeries.E2_MICRO,
            CustomMachineType.CPUSeries.E2_MEDIUM,
        )

    def _check_extra_memory(self) -> bool:
        if self._checked:
            return self.memory_mb > self.core_count * self.limits.max_mem_per_core
        else:
            raise RuntimeError(
                "You need to call _check_parameters() before calling _check_extra_memory()"
            )

    def _check_parameters(self):
        """
        Check whether the requested parameters are allowed. Find more information about limitations of custom machine
        types at: https://cloud.google.com/compute/docs/general-purpose-machines#custom_machine_types
        """
        # Check the number of cores
        if (
            self.limits.allowed_cores
            and self.core_count not in self.limits.allowed_cores
        ):
            raise RuntimeError(
                f"Invalid number of cores requested. Allowed number of cores for {self.cpu_series.name} is: {sorted(self.limits.allowed_cores)}"
            )

        # Memory must be a multiple of 256 MB
        if self.memory_mb % 256 != 0:
            raise RuntimeError("Requested memory must be a multiple of 256 MB.")

        # Check if the requested memory isn't too little
        if self.memory_mb < self.core_count * self.limits.min_mem_per_core:
            raise RuntimeError(
                f"Requested memory is too low. Minimal memory for {self.cpu_series.name} is {self.limits.min_mem_per_core} MB per core."
            )

        # Check if the requested memory isn't too much
        if self.memory_mb > self.core_count * self.limits.max_mem_per_core:
            if self.limits.allow_extra_memory:
                if self.memory_mb > self.limits.extra_memory_limit:
                    raise RuntimeError(
                        f"Requested memory is too large.. Maximum memory allowed for {self.cpu_series.name} is {self.limits.extra_memory_limit} MB."
                    )
            else:
                raise RuntimeError(
                    f"Requested memory is too large.. Maximum memory allowed for {self.cpu_series.name} is {self.limits.max_mem_per_core} MB per core."
                )

        self._checked = True

    def __str__(self) -> str:
        """
        Return the custom machine type in form of a string acceptable by Compute Engine API.
        """
        if self.cpu_series in {
            self.CPUSeries.E2_SMALL,
            self.CPUSeries.E2_MICRO,
            self.CPUSeries.E2_MEDIUM,
        }:
            return f"zones/{self.zone}/machineTypes/{self.cpu_series.value}-{self.memory_mb}"

        if self.extra_memory_used:
            return f"zones/{self.zone}/machineTypes/{self.cpu_series.value}-{self.core_count}-{self.memory_mb}-ext"

        return f"zones/{self.zone}/machineTypes/{self.cpu_series.value}-{self.core_count}-{self.memory_mb}"

    def short_type_str(self) -> str:
        """
        Return machine type in a format without the zone. For example, n2-custom-0-10240.
        This format is used to create instance templates.
        """
        return str(self).rsplit("/", maxsplit=1)[1]

    @classmethod
    def from_str(cls, machine_type: str):
        """
        Construct a new object from a string. The string needs to be a valid custom machine type like:
         - https://www.googleapis.com/compute/v1/projects/diregapic-mestiv/zones/us-central1-b/machineTypes/e2-custom-4-8192
         - zones/us-central1-b/machineTypes/e2-custom-4-8192
         - e2-custom-4-8192 (in this case, the zone parameter will not be set)
        """
        zone = None
        if machine_type.startswith("http"):
            machine_type = machine_type[machine_type.find("zones/") :]

        if machine_type.startswith("zones/"):
            _, zone, _, machine_type = machine_type.split("/")

        extra_mem = machine_type.endswith("-ext")

        if machine_type.startswith("custom"):
            cpu = cls.CPUSeries.N1
            _, cores, memory = machine_type.rsplit("-", maxsplit=2)
        else:
            if extra_mem:
                cpu_series, _, cores, memory, _ = machine_type.split("-")
            else:
                cpu_series, _, cores, memory = machine_type.split("-")
            if cpu_series == "n2":
                cpu = cls.CPUSeries.N2
            elif cpu_series == "n2d":
                cpu = cls.CPUSeries.N2D
            elif cpu_series == "e2":
                cpu = cls.CPUSeries.E2
                if cores == "micro":
                    cpu = cls.CPUSeries.E2_MICRO
                    cores = 2
                elif cores == "small":
                    cpu = cls.CPUSeries.E2_SMALL
                    cores = 2
                elif cores == "medium":
                    cpu = cls.CPUSeries.E2_MEDIUM
                    cores = 2
            else:
                raise RuntimeError("Unknown CPU series.")

        cores = int(cores)
        memory = int(memory)

        return cls(zone, cpu, memory, cores)


def get_image_from_family(project: str, family: str) -> compute_v1.Image:
    """
    Retrieve the newest image that is part of a given family in a project.

    Args:
        project: project ID or project number of the Cloud project you want to get image from.
        family: name of the image family you want to get image from.

    Returns:
        An Image object.
    """
    image_client = compute_v1.ImagesClient()
    # List of public operating system (OS) images: https://cloud.google.com/compute/docs/images/os-details
    newest_image = image_client.get_from_family(project=project, family=family)
    return newest_image


def disk_from_image(
    disk_type: str,
    disk_size_gb: int,
    boot: bool,
    source_image: str,
    auto_delete: bool = True,
) -> compute_v1.AttachedDisk:
    """
    Create an AttachedDisk object to be used in VM instance creation. Uses an image as the
    source for the new disk.

    Args:
         disk_type: the type of disk you want to create. This value uses the following format:
            "zones/{zone}/diskTypes/(pd-standard|pd-ssd|pd-balanced|pd-extreme)".
            For example: "zones/us-west3-b/diskTypes/pd-ssd"
        disk_size_gb: size of the new disk in gigabytes
        boot: boolean flag indicating whether this disk should be used as a boot disk of an instance
        source_image: source image to use when creating this disk. You must have read access to this disk. This can be one
            of the publicly available images or an image from one of your projects.
            This value uses the following format: "projects/{project_name}/global/images/{image_name}"
        auto_delete: boolean flag indicating whether this disk should be deleted with the VM that uses it

    Returns:
        AttachedDisk object configured to be created using the specified image.
    """
    boot_disk = compute_v1.AttachedDisk()
    initialize_params = compute_v1.AttachedDiskInitializeParams()
    initialize_params.source_image = source_image
    initialize_params.disk_size_gb = disk_size_gb
    initialize_params.disk_type = disk_type
    boot_disk.initialize_params = initialize_params
    # Remember to set auto_delete to True if you want the disk to be deleted when you delete
    # your VM instance.
    boot_disk.auto_delete = auto_delete
    boot_disk.boot = boot
    return boot_disk


def wait_for_extended_operation(
    operation: ExtendedOperation, verbose_name: str = "operation", timeout: int = 300
) -> Any:
    """
    Waits for the extended (long-running) operation to complete.

    If the operation is successful, it will return its result.
    If the operation ends with an error, an exception will be raised.
    If there were any warnings during the execution of the operation
    they will be printed to sys.stderr.

    Args:
        operation: a long-running operation you want to wait on.
        verbose_name: (optional) a more verbose name of the operation,
            used only during error and warning reporting.
        timeout: how long (in seconds) to wait for operation to finish.
            If None, wait indefinitely.

    Returns:
        Whatever the operation.result() returns.

    Raises:
        This method will raise the exception received from `operation.exception()`
        or RuntimeError if there is no exception set, but there is an `error_code`
        set for the `operation`.

        In case of an operation taking longer than `timeout` seconds to complete,
        a `concurrent.futures.TimeoutError` will be raised.
    """
    result = operation.result(timeout=timeout)

    if operation.error_code:
        print(
            f"Error during {verbose_name}: [Code: {operation.error_code}]: {operation.error_message}",
            file=sys.stderr,
            flush=True,
        )
        print(f"Operation ID: {operation.name}", file=sys.stderr, flush=True)
        raise operation.exception() or RuntimeError(operation.error_message)

    if operation.warnings:
        print(f"Warnings during {verbose_name}:\n", file=sys.stderr, flush=True)
        for warning in operation.warnings:
            print(f" - {warning.code}: {warning.message}", file=sys.stderr, flush=True)

    return result


def create_instance(
    project_id: str,
    zone: str,
    instance_name: str,
    disks: list[compute_v1.AttachedDisk],
    machine_type: str = "n1-standard-1",
    network_link: str = "global/networks/default",
    subnetwork_link: str = None,
    internal_ip: str = None,
    external_access: bool = False,
    external_ipv4: str = None,
    accelerators: list[compute_v1.AcceleratorConfig] = None,
    preemptible: bool = False,
    spot: bool = False,
    instance_termination_action: str = "STOP",
    custom_hostname: str = None,
    delete_protection: bool = False,
) -> compute_v1.Instance:
    """
    Send an instance creation request to the Compute Engine API and wait for it to complete.

    Args:
        project_id: project ID or project number of the Cloud project you want to use.
        zone: name of the zone to create the instance in. For example: "us-west3-b"
        instance_name: name of the new virtual machine (VM) instance.
        disks: a list of compute_v1.AttachedDisk objects describing the disks
            you want to attach to your new instance.
        machine_type: machine type of the VM being created. This value uses the
            following format: "zones/{zone}/machineTypes/{type_name}".
            For example: "zones/europe-west3-c/machineTypes/f1-micro"
        network_link: name of the network you want the new instance to use.
            For example: "global/networks/default" represents the network
            named "default", which is created automatically for each project.
        subnetwork_link: name of the subnetwork you want the new instance to use.
            This value uses the following format:
            "regions/{region}/subnetworks/{subnetwork_name}"
        internal_ip: internal IP address you want to assign to the new instance.
            By default, a free address from the pool of available internal IP addresses of
            used subnet will be used.
        external_access: boolean flag indicating if the instance should have an external IPv4
            address assigned.
        external_ipv4: external IPv4 address to be assigned to this instance. If you specify
            an external IP address, it must live in the same region as the zone of the instance.
            This setting requires `external_access` to be set to True to work.
        accelerators: a list of AcceleratorConfig objects describing the accelerators that will
            be attached to the new instance.
        preemptible: boolean value indicating if the new instance should be preemptible
            or not. Preemptible VMs have been deprecated and you should now use Spot VMs.
        spot: boolean value indicating if the new instance should be a Spot VM or not.
        instance_termination_action: What action should be taken once a Spot VM is terminated.
            Possible values: "STOP", "DELETE"
        custom_hostname: Custom hostname of the new VM instance.
            Custom hostnames must conform to RFC 1035 requirements for valid hostnames.
        delete_protection: boolean value indicating if the new virtual machine should be
            protected against deletion or not.
    Returns:
        Instance object.
    """
    instance_client = compute_v1.InstancesClient()

    # Use the network interface provided in the network_link argument.
    network_interface = compute_v1.NetworkInterface()
    network_interface.network = network_link
    if subnetwork_link:
        network_interface.subnetwork = subnetwork_link

    if internal_ip:
        network_interface.network_i_p = internal_ip

    if external_access:
        access = compute_v1.AccessConfig()
        access.type_ = compute_v1.AccessConfig.Type.ONE_TO_ONE_NAT.name
        access.name = "External NAT"
        access.network_tier = access.NetworkTier.PREMIUM.name
        if external_ipv4:
            access.nat_i_p = external_ipv4
        network_interface.access_configs = [access]

    # Collect information into the Instance object.
    instance = compute_v1.Instance()
    instance.network_interfaces = [network_interface]
    instance.name = instance_name
    instance.disks = disks
    if re.match(r"^zones/[a-z\d\-]+/machineTypes/[a-z\d\-]+$", machine_type):
        instance.machine_type = machine_type
    else:
        instance.machine_type = f"zones/{zone}/machineTypes/{machine_type}"

    instance.scheduling = compute_v1.Scheduling()
    if accelerators:
        instance.guest_accelerators = accelerators
        instance.scheduling.on_host_maintenance = (
            compute_v1.Scheduling.OnHostMaintenance.TERMINATE.name
        )

    if preemptible:
        # Set the preemptible setting
        warnings.warn(
            "Preemptible VMs are being replaced by Spot VMs.", DeprecationWarning
        )
        instance.scheduling = compute_v1.Scheduling()
        instance.scheduling.preemptible = True

    if spot:
        # Set the Spot VM setting
        instance.scheduling.provisioning_model = (
            compute_v1.Scheduling.ProvisioningModel.SPOT.name
        )
        instance.scheduling.instance_termination_action = instance_termination_action

    if custom_hostname is not None:
        # Set the custom hostname for the instance
        instance.hostname = custom_hostname

    if delete_protection:
        # Set the delete protection bit
        instance.deletion_protection = True

    # Prepare the request to insert an instance.
    request = compute_v1.InsertInstanceRequest()
    request.zone = zone
    request.project = project_id
    request.instance_resource = instance

    # Wait for the create operation to complete.
    print(f"Creating the {instance_name} instance in {zone}...")

    operation = instance_client.insert(request=request)

    wait_for_extended_operation(operation, "instance creation")

    print(f"Instance {instance_name} created.")
    return instance_client.get(project=project_id, zone=zone, instance=instance_name)


def create_custom_shared_core_instance(
    project_id: str,
    zone: str,
    instance_name: str,
    cpu_series: CustomMachineType.CPUSeries,
    memory: int,
) -> compute_v1.Instance:
    """
    Create a new VM instance with a custom type using shared CPUs.

    Args:
        project_id: project ID or project number of the Cloud project you want to use.
        zone: name of the zone to create the instance in. For example: "us-west3-b"
        instance_name: name of the new virtual machine (VM) instance.
        cpu_series: the type of CPU you want to use. Pick one value from the CustomMachineType.CPUSeries enum.
            For example: CustomMachineType.CPUSeries.E2_MICRO
        memory: the amount of memory for the VM instance, in megabytes.

    Return:
        Instance object.
    """
    assert cpu_series in (
        CustomMachineType.CPUSeries.E2_MICRO,
        CustomMachineType.CPUSeries.E2_SMALL,
        CustomMachineType.CPUSeries.E2_MEDIUM,
    )
    custom_type = CustomMachineType(zone, cpu_series, memory)

    newest_debian = get_image_from_family(project="debian-cloud", family="debian-10")
    disk_type = f"zones/{zone}/diskTypes/pd-standard"
    disks = [disk_from_image(disk_type, 10, True, newest_debian.self_link)]

    return create_instance(project_id, zone, instance_name, disks, str(custom_type))


# [END compute_custom_machine_type_create_shared_with_helper]
