[CmdletBinding()]
param(
    [string] $Client,
    [string] $Scope,
    [string] $Version = "v1.0.0",
    [switch] $Update,
    [string] $AssetDirectory
)

$ErrorActionPreference = "Stop"
$PackageBaseUrl = "https://gitlab.com/api/v4/projects/85407514/packages/generic/create-issue"

function Receive-BoundedAsset {
    param(
        [Parameter(Mandatory = $true)] [uri] $Uri,
        [Parameter(Mandatory = $true)] [string] $DestinationPath,
        [Parameter(Mandatory = $true)] [long] $MaximumBytes
    )

    $Client = [System.Net.Http.HttpClient]::new()
    $Response = $null
    $InputStream = $null
    $OutputStream = $null
    try {
        $Response = $Client.GetAsync(
            $Uri, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead
        ).GetAwaiter().GetResult()
        $Response.EnsureSuccessStatusCode() | Out-Null
        if ($Response.Content.Headers.ContentLength -gt $MaximumBytes) {
            throw "Download exceeds the $MaximumBytes-byte safety limit: $Uri"
        }
        $InputStream = $Response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
        $OutputStream = [System.IO.File]::Create($DestinationPath)
        $Buffer = [byte[]]::new(65536)
        [long] $Total = 0
        while (($Read = $InputStream.Read($Buffer, 0, $Buffer.Length)) -gt 0) {
            $Total += $Read
            if ($Total -gt $MaximumBytes) {
                throw "Download exceeds the $MaximumBytes-byte safety limit: $Uri"
            }
            $OutputStream.Write($Buffer, 0, $Read)
        }
    }
    finally {
        if ($OutputStream) { $OutputStream.Dispose() }
        if ($InputStream) { $InputStream.Dispose() }
        if ($Response) { $Response.Dispose() }
        $Client.Dispose()
    }
}

function Assert-SafeDestinationParent {
    param(
        [Parameter(Mandatory = $true)] [string] $SelectedRoot,
        [Parameter(Mandatory = $true)] [AllowEmptyString()] [string] $RelativeParent
    )

    # Split without RemoveEmptyEntries: a `.`, `..`, or empty segment, including the one a
    # leading or trailing separator produces, is rejected rather than skipped.
    $Components = $RelativeParent.Split([char[]] @("/", "\"))
    foreach ($Component in $Components) {
        if ($Component -eq "" -or $Component -eq "." -or $Component -eq "..") {
            throw "Client destination '$RelativeParent' is not a safe relative path; nothing was written"
        }
    }

    $RootPath = [System.IO.Path]::GetFullPath($SelectedRoot)
    $ParentPath = [System.IO.Path]::GetFullPath((Join-Path $RootPath $RelativeParent))
    $Separator = [System.IO.Path]::DirectorySeparatorChar
    $RootPrefix = $RootPath.TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    ) + $Separator
    $Comparison = if ($IsWindows) {
        [System.StringComparison]::OrdinalIgnoreCase
    } else {
        [System.StringComparison]::Ordinal
    }
    if (-not $ParentPath.StartsWith($RootPrefix, $Comparison)) {
        throw "Installer destination escapes the selected installation root"
    }

    $Current = $RootPath
    foreach ($Component in $Components) {
        $Current = Join-Path $Current $Component
        $Item = Get-Item -LiteralPath $Current -Force -ErrorAction SilentlyContinue
        if ($null -ne $Item -and
            0 -ne ($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw "$Current is a symbolic-link or reparse-point ancestor; replace it manually before installing"
        }
        if ($null -ne $Item -and -not $Item.PSIsContainer) {
            throw "$Current is not a directory; replace it manually before installing"
        }
    }
    return $ParentPath
}

if ($Version -cnotmatch '^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$') {
    throw "-Version must be a semantic version such as v1.0.0"
}

# Generated from release-contract.json; tests require an exact match.
$ClientRootEntries = "claude-code=.claude/skills codex=.agents/skills cursor=.agents/skills gemini=.agents/skills"
$ClientLabelEntries = "claude-code=Claude Code|codex=Codex|cursor=Cursor|gemini=Gemini CLI"
$UnsupportedClientEntries = "claude-chat"
$ClientRoots = @{}
$SupportedClients = @()
foreach ($Entry in $ClientRootEntries.Split(" ")) {
    $Parts = $Entry.Split("=", 2)
    $ClientRoots[$Parts[0]] = $Parts[1]
    $SupportedClients += $Parts[0]
}
$UnsupportedClients = $UnsupportedClientEntries.Split(" ")
$Guided = [string]::IsNullOrWhiteSpace($Client) -or [string]::IsNullOrWhiteSpace($Scope)
if ($Guided -and [Console]::IsInputRedirected) {
    throw "-Client and -Scope are required in non-interactive mode"
}

if ([string]::IsNullOrWhiteSpace($Client)) {
    Write-Host "Choose your AI client:"
    foreach ($Entry in $ClientLabelEntries.Split("|")) {
        $Parts = $Entry.Split("=", 2)
        Write-Host ("  {0,-18} {1}" -f $Parts[0], $Parts[1])
    }
    for ($Attempt = 0; $Attempt -lt 3; $Attempt++) {
        $Client = Read-Host "Client ID"
        if (-not [string]::IsNullOrWhiteSpace($Client) -and
            $ClientRoots.ContainsKey($Client.ToLowerInvariant())) { break }
        Write-Host "Unsupported client ID '$Client'. Try again."
    }
    if ([string]::IsNullOrWhiteSpace($Client) -or
        -not $ClientRoots.ContainsKey($Client.ToLowerInvariant())) {
        throw "No supported client was selected after 3 attempts; no files were changed"
    }
}

if ([string]::IsNullOrWhiteSpace($Scope)) {
    for ($Attempt = 0; $Attempt -lt 3; $Attempt++) {
        $Scope = Read-Host "Install for this user or this project? [user/project]"
        if ($Scope -in @("user", "project")) { break }
        Write-Host "Scope must be 'user' or 'project'. Try again."
    }
    if ($Scope -notin @("user", "project")) {
        throw "No valid scope was selected after 3 attempts; no files were changed"
    }
}

$Client = $Client.ToLowerInvariant()
$Scope = $Scope.ToLowerInvariant()

if ($ClientRoots.ContainsKey($Client)) {
    $SkillRoot = $ClientRoots[$Client]
} elseif ($UnsupportedClients -contains $Client) {
    throw "Client '$Client' has no local skill directory. See https://gitlab.com/hubertgajewski-ai/create-issue/-/blob/main/docs/installation.md#other-installation-environments"
} else {
    throw "Unsupported client '$Client'; supported clients: $($SupportedClients -join ', ')"
}

if ($Scope -eq "user") {
    if ([string]::IsNullOrWhiteSpace($HOME)) {
        throw "HOME is not set; cannot resolve the user installation directory"
    }
    $Root = $HOME
} else {
    if ($Scope -ne "project") {
        throw "-Scope must be 'User' or 'Project'"
    }
    $Root = (Get-Location).Path
}
$Root = [System.IO.Path]::GetFullPath($Root)
$Parent = Assert-SafeDestinationParent -SelectedRoot $Root -RelativeParent $SkillRoot
$Destination = Join-Path $Parent "create-issue"
$Existing = Get-Item -LiteralPath $Destination -Force -ErrorAction SilentlyContinue
if ($null -ne $Existing -and -not $Update) {
    throw "$Destination already exists; inspect the new release, then rerun with -Update to replace it"
}
if ($null -ne $Existing -and
    0 -ne ($Existing.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
    throw "$Destination is a symbolic link or reparse point; replace it manually before using -Update"
}

if ($Guided) {
    Write-Host ""
    Write-Host "Client: $Client"
    Write-Host "Scope: $Scope"
    Write-Host "Destination: $Destination"
    Write-Host "Release: $Version"
    $Confirmation = Read-Host "Continue? [y/N]"
    if ($Confirmation -notin @("y", "Y", "yes", "YES", "Yes")) {
        throw "Installation cancelled; no files were changed"
    }
}

$Archive = "create-issue-$Version.zip"
$Checksum = "$Archive.sha256"
$TemporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("create-issue-install-" + [guid]::NewGuid())
$Stage = $null
$Backup = $null
$Activated = $false
$ActivationOwned = $false
$Lock = $null
$LockOwned = $false
$MarkerName = ".create-issue-installing"
$StageLeaf = $null

try {
    New-Item -ItemType Directory -Path $TemporaryRoot | Out-Null
    $ArchivePath = Join-Path $TemporaryRoot $Archive
    $ChecksumPath = Join-Path $TemporaryRoot $Checksum

    if ($AssetDirectory) {
        $OfflineArchive = Join-Path $AssetDirectory $Archive
        $OfflineChecksum = Join-Path $AssetDirectory $Checksum
        if (-not (Test-Path -LiteralPath $OfflineArchive -PathType Leaf)) {
            throw "Offline archive not found: $OfflineArchive"
        }
        if (-not (Test-Path -LiteralPath $OfflineChecksum -PathType Leaf)) {
            throw "Offline checksum not found: $OfflineChecksum"
        }
        Copy-Item -LiteralPath $OfflineArchive -Destination $ArchivePath
        Copy-Item -LiteralPath $OfflineChecksum -Destination $ChecksumPath
    } else {
        $PackageVersion = $Version.Substring(1)
        $AssetUrl = "$PackageBaseUrl/$PackageVersion"
        try {
            Receive-BoundedAsset -Uri "$AssetUrl/$Archive" -DestinationPath $ArchivePath -MaximumBytes 67108864
            Receive-BoundedAsset -Uri "$AssetUrl/$Checksum" -DestinationPath $ChecksumPath -MaximumBytes 4096
        } catch {
            throw "Failed to download release assets for $Version`: $($_.Exception.Message)"
        }
    }

    $Expected = ((Get-Content -LiteralPath $ChecksumPath -TotalCount 1) -split '\s+')[0]
    if ($Expected -cnotmatch '^[0-9a-f]{64}$') {
        throw "The checksum file for $Version is malformed"
    }
    $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $ArchivePath).Hash.ToLowerInvariant()
    if ($Actual -cne $Expected) {
        throw "Checksum mismatch for $Archive`: expected $Expected, got $Actual; no files were installed"
    }

    $Zip = [System.IO.Compression.ZipFile]::OpenRead($ArchivePath)
    try {
        if ($Zip.Entries.Count -gt 10000) {
            throw "Release package exceeds the 10000-entry safety limit"
        }
        [long] $ExpandedBytes = 0
        foreach ($Entry in $Zip.Entries) {
            $EntryPath = $Entry.FullName.Replace("\", "/")
            # A directory entry ends in one `/`; any other empty segment is unsafe.
            if ($EntryPath.EndsWith("/")) {
                $EntryPath = $EntryPath.Substring(0, $EntryPath.Length - 1)
            }
            $Parts = $EntryPath.Split("/")
            if ($Parts[0] -cne "create-issue" -or
                $Parts -contains "" -or $Parts -contains ".." -or $Parts -contains ".") {
                throw "Release package contains an unsafe path: $EntryPath"
            }
            $ExpandedBytes += $Entry.Length
            if ($ExpandedBytes -gt 134217728) {
                throw "Release package exceeds the 134217728-byte extraction safety limit"
            }
        }
    }
    finally {
        $Zip.Dispose()
    }
    $Extracted = Join-Path $TemporaryRoot "extracted"
    Expand-Archive -LiteralPath $ArchivePath -DestinationPath $Extracted
    $Package = Join-Path $Extracted "create-issue"
    if (-not (Test-Path -LiteralPath (Join-Path $Package "SKILL.md") -PathType Leaf)) {
        throw "Release package is missing create-issue/SKILL.md"
    }
    $ManifestPath = Join-Path $Package ".claude-plugin/plugin.json"
    if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
        throw "Release package is missing version metadata"
    }
    foreach ($RequiredDirectory in @("references", "scripts", "agents")) {
        if (-not (Test-Path -LiteralPath (Join-Path $Package $RequiredDirectory) -PathType Container)) {
            throw "Release package is missing create-issue/$RequiredDirectory/"
        }
    }
    $Links = Get-ChildItem -LiteralPath $Package -Recurse -Force | Where-Object {
        0 -ne ($_.Attributes -band [System.IO.FileAttributes]::ReparsePoint)
    }
    if ($Links) {
        throw "Release package contains symbolic links or reparse points"
    }
    try {
        $ManifestVersion = (Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json).version
    } catch {
        throw "Release package version metadata is malformed"
    }
    if ($ManifestVersion -cne $Version.Substring(1)) {
        throw "Release package version does not match requested version $Version"
    }

    $CheckedParent = Assert-SafeDestinationParent -SelectedRoot $Root -RelativeParent $SkillRoot
    if ($CheckedParent -cne $Parent) {
        throw "Installer destination changed while the package was being verified"
    }
    New-Item -ItemType Directory -Force -Path $Parent | Out-Null
    $CheckedParent = Assert-SafeDestinationParent -SelectedRoot $Root -RelativeParent $SkillRoot
    if ($CheckedParent -cne $Parent) {
        throw "Installer destination changed while the package was being verified"
    }
    $Stage = Join-Path $Parent (".create-issue.stage." + [guid]::NewGuid())
    $Lock = Join-Path $Parent ".create-issue.install.lock"
    try {
        New-Item -ItemType Directory -Path $Lock | Out-Null
        $LockOwned = $true
        Set-Content -LiteralPath (Join-Path $Lock "owner") -Value $PID -NoNewline
    } catch {
        throw "Another installation is active or left $Lock; verify no installer is running before removing that lock"
    }
    New-Item -ItemType Directory -Path $Stage | Out-Null
    Get-ChildItem -LiteralPath $Package -Force | Copy-Item -Recurse -Force -Destination $Stage
    $MarkerPath = Join-Path $Stage $MarkerName
    if (Test-Path -LiteralPath $MarkerPath) {
        throw "Release package contains the reserved activation marker"
    }
    New-Item -ItemType File -Path $MarkerPath | Out-Null
    $StageLeaf = Split-Path -Leaf $Stage

    $CheckedParent = Assert-SafeDestinationParent -SelectedRoot $Root -RelativeParent $SkillRoot
    if ($CheckedParent -cne $Parent) {
        throw "Installer destination changed while the package was being verified"
    }
    $CurrentDestination = Get-Item -LiteralPath $Destination -Force -ErrorAction SilentlyContinue
    if ($null -ne $CurrentDestination -and -not $Update) {
        throw "$Destination appeared while the package was being verified; no files were installed"
    }
    if ($null -ne $CurrentDestination -and
        0 -ne ($CurrentDestination.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        throw "$Destination became a symbolic link or reparse point while the package was being verified; no files were installed"
    }
    if ($null -ne $CurrentDestination) {
        $Backup = Join-Path $Parent (".create-issue.backup." + [guid]::NewGuid())
        New-Item -ItemType Directory -Path $Backup | Out-Null
        Move-Item -LiteralPath $Destination -Destination (Join-Path $Backup "create-issue")
    }
    $CheckedParent = Assert-SafeDestinationParent -SelectedRoot $Root -RelativeParent $SkillRoot
    if ($CheckedParent -cne $Parent) {
        throw "Installer destination changed during activation"
    }
    Move-Item -LiteralPath $Stage -Destination $Destination
    $ActivatedMarker = Join-Path $Destination $MarkerName
    if (-not (Test-Path -LiteralPath $ActivatedMarker -PathType Leaf)) {
        throw "Destination changed during activation; the staged package was not activated"
    }
    $ActivationOwned = $true
    $Stage = $null
    if (-not (Test-Path -LiteralPath (Join-Path $Destination "SKILL.md") -PathType Leaf)) {
        throw "Activated installation failed final validation"
    }
    Remove-Item -Force -LiteralPath $ActivatedMarker
    $ActivationOwned = $false
    $Activated = $true
    if ($Backup) {
        try {
            Remove-Item -Recurse -Force -LiteralPath $Backup
            $Backup = $null
        } catch {
            Write-Warning "Installed successfully, but the previous installation could not be removed from $(Join-Path $Backup 'create-issue')"
        }
    }

    $FirstCommand = switch ($Client) {
        "claude-code" { '/create-issue <what the issue is about>' }
        "codex" { '$create-issue <what the issue is about>' }
        "cursor" { '/create-issue <what the issue is about> in Agent chat' }
        default { 'Describe the issue you want drafted and approve the create-issue activation prompt' }
    }

    Write-Output "Installed Create Issue $Version"
    Write-Output "Destination: $Destination"
    Write-Output "Verification: SHA-256 $Actual"
    Write-Output "First draft: $FirstCommand"
}
catch {
    if (-not $Activated -and $ActivationOwned -and
        (Test-Path -LiteralPath (Join-Path $Destination $MarkerName) -PathType Leaf)) {
        Remove-Item -Recurse -Force -LiteralPath $Destination -ErrorAction SilentlyContinue
    }
    if (-not $Activated -and $StageLeaf) {
        $NestedStage = Join-Path $Destination $StageLeaf
        if (Test-Path -LiteralPath (Join-Path $NestedStage $MarkerName) -PathType Leaf) {
            Remove-Item -Recurse -Force -LiteralPath $NestedStage -ErrorAction SilentlyContinue
        }
    }
    if (-not $Activated -and $Backup) {
        $BackedUpDestination = Join-Path $Backup "create-issue"
        if ((Test-Path -LiteralPath $BackedUpDestination) -and -not (Test-Path -LiteralPath $Destination)) {
            Move-Item -LiteralPath $BackedUpDestination -Destination $Destination -ErrorAction SilentlyContinue
        }
    }
    throw
}
finally {
    if ($Stage) {
        Remove-Item -Recurse -Force -LiteralPath $Stage -ErrorAction SilentlyContinue
    }
    if ($Backup -and -not (Test-Path -LiteralPath (Join-Path $Backup "create-issue"))) {
        Remove-Item -Recurse -Force -LiteralPath $Backup -ErrorAction SilentlyContinue
    }
    if ($Backup -and (Test-Path -LiteralPath (Join-Path $Backup "create-issue"))) {
        Write-Warning "Previous installation preserved at $(Join-Path $Backup 'create-issue')"
    }
    if ($LockOwned -and $Lock) {
        Remove-Item -Force -LiteralPath (Join-Path $Lock "owner") -ErrorAction SilentlyContinue
        Remove-Item -Force -LiteralPath $Lock -ErrorAction SilentlyContinue
    }
    Remove-Item -Recurse -Force -LiteralPath $TemporaryRoot -ErrorAction SilentlyContinue
}
