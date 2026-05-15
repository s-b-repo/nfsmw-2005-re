# NFSMW SDK Quick Reference

Concise lookup card consolidated from `sdk_addrs.json` (181 entries), `attribute_cracks_verified.json` (294 names) and `sdk_enums.json` (65 enums).

All addresses are speed.exe (1.3, EN). Header column refers to the SDK header tree.

---

## 1. Tweak globals + Draw* flags

Live mod knobs. Type comes from `sdk_addrs.json`. Defaults annotated where commonly known from the binary.

| Address | Type | Name | Default | Notes |
|---------|------|------|---------|-------|
| 0x901aec | float | `Tweak_GameBreakerCollisionMass` | 1.0 | Mass multiplier when speedbreaker triggers a smash |
| 0x901b1c | float | `Tweak_GameSpeed` | 1.0 | Global wall-clock multiplier; 0 = pause |
| 0x92584c | bool | `Tweak_PauseCameraLock` | false | Lock camera while paused |
| 0x937804 | bool | `Tweak_InfiniteNOS` | false | NOS bar never depletes |
| 0x988e1c | bool | `Tweak_InfiniteRaceBreaker` | false | Speedbreaker never depletes |
| 0x57caa8 | bool | `DrawHUD` | true | Master HUD toggle |
| 0x903320 | bool | `DrawCars` | true | Draw all cars |
| 0x903324 | bool | `DrawCarsReflections` | true | Reflective pass for cars |
| 0x903328 | bool | `DrawCarShadow` | true | Per-car shadow projection |
| 0x8f2918 | bool | `DrawLightFlares` | true | Headlight + sun flares |
| 0x903384 | CARPART_LOD | `ForceCarLOD` | -1 | Pin car LOD bucket (0..3) |
| 0x903388 | CARPART_LOD | `ForceTireLOD` | -1 | Pin tire LOD bucket |
| 0x904aec | float | `AnimationSpeed` | 1.0 | Multiplier for EAGL4Anim ticks |
| 0x91112c | uint16 | `NOSFOVWidening` | 30 | FOV punch (deg) on NOS engaged |
| 0x911020 | bool | `StopUpdatingCamera` | false | Freeze cam at current pose |
| 0x91606c | bool | `IsInNIS` | false | Non-Interactive Sequence playing |
| 0x91cae4 | bool | `IsFadeScreenOn` | false | Fade overlay active |
| 0x982c50 | bool | `WindowHasLostFocus` | false | Set by WndProc WM_KILLFOCUS |
| 0x8fae44 | ePrecullerMode | `PrecullerMode` | 0 | Visibility preculler mode |
| 0x8f86a8 | const char* | `SkipFEPlayerCar` | NULL | If non-NULL, bypass FE & spawn this car |
| 0x8f86c0 | bool | `SkipFEDisableCops` | false | FE-skip cop disable flag |
| 0x8f86c4 | ePlayerSettingsCameras | `SkipFEPOVType` | Close | FE-skip default cam |
| 0x926064 | bool | `SkipFE` | false | Master front-end bypass |
| 0x926090 | float | `SkipFETrafficDensity` | 0.5 | FE-skip traffic density |
| 0x926094 | bool | `SkipFEDisableTraffic` | false | FE-skip traffic kill |
| 0x9b34b0 | Math::Matrix4 | `CarScaleMatrix` | identity | Scale applied to every car draw |

---

## 2. Singleton pointers

The big globals you `mov eax, [addr]; mov eax, [eax]` against.

| Address | Type | Name | Use |
|---------|------|------|-----|
| 0x925e90 | GameFlowState* | `TheGameFlowManager` | Top-level state-machine root (Boot/FE/InGame/Race…) |
| 0x90d5f4 | AICopManager* | `TheOneCopManager` | Cop AI singleton — spawn lists, heat, pursuit registry |
| 0x91cf90 | cFrontEndDatabase* | `CFEManager` | Front-end DB (`GetPlayerSettings`) |
| 0x90d8e4 | GPS* | `GPS` | GPS line + navigation arrow |
| 0x90dcbc | Database* | `Attrib::Database` | Root attributes DB (`GetClass`) |
| 0x91e000 | GRaceStatus* | `g_pGRaceStatus` | Race state — barriers, mode, context |
| 0x91e00c | GManager* | `g_pGManager` | World icon/character manager |
| 0x92d87c | IPlayer* (vtbl) | `IPlayer` | Player interface pool |
| 0x9352b0 | PVehicle* (vtbl) | `PVehicle` | Per-vehicle interface pool |
| 0x9383b0 | Volatile* | `Volatile::RemoveStatusPrev` | RigidBody status set |
| 0x9384b0 | Volatile* | `Volatile::RemoveStatus` | SimpleRigidBody status set |
| 0x9b08f8 | DebugVehicleSelection* | `DebugVehicleSelection` | Dev-only car swap |
| 0x9b392c | TimeOfDay* | `TimeOfDay::GetInstance` | TOD singleton |

---

## 3. Key class & cast-helper addresses

Interface vtables sit on the right of `0x891000`. `…Cast_t` symbols are RTTI helpers used by `IsA<>()` lookups.

| Address | Class | Header |
|---------|-------|--------|
| 0x891a80 | AIVehicleCast_t | Extensions.h |
| 0x891bb8 | AIVehiclePidCast_t | Extensions.h |
| 0x891cf8 | AIVehicleTrafficCast_t | Extensions.h |
| 0x891ec0 | AIVehiclePursuitCast_t | Extensions.h |
| 0x8920d8 | AIVehicleHelicopterCast_t | Extensions.h |
| 0x892560 | AIVehicleCopCarCast_t | Extensions.h |
| 0x892720 | AIVehicleRacecarCast_t | Extensions.h |
| 0x892ad0 | AIVehicleHumanCast_t | Extensions.h |
| 0x892e28 | AIVehicleEmptyCast_t | Extensions.h |
| 0x8aa6d0 | RBSmackableCast_t | Extensions.h |
| 0x8ab598 | PInputCast_t | Extensions.h |
| 0x8ac448 | RigidBodyCast_t | Extensions.h |
| 0x8ac5fc | SimpleRigidBodyCast_t | Extensions.h |
| 0x8ac6bc | InputPlayerCast_t | Extensions.h |
| 0x8ac938 | RBVehicleCast_t | Extensions.h |
| 0x8acba8 | RBTractorCast_t | Extensions.h |
| 0x8ad3c4 | DamageHeliCast_t | Extensions.h |
| 0x8ad438 | DamageCopCarCast_t | Extensions.h |
| 0x8ad6ac | DamageDragsterCast_t | Extensions.h |
| 0x8b0b10 | ValidatePlayer_t::GetPlayerInstance | Extensions.h |
| 0x8b0bb0 | LocalPlayerCast_t | Extensions.h |
| 0x9352b0 | PVehicle (vtbl group) | Types/PVehicle.h |
| 0x92d87c | IPlayer (vtbl) | Types/IPlayer.h |

**Live runtime vtables (from runtime_trace memory):**

| Address | Class | Notes |
|---------|-------|-------|
| 0x8ac06c | vtbl_pvehicle_PlayerCar | Player chassis vtable |
| 0x8ac0fc | vtbl_pvehicle_AICar | AI chassis vtable |
| 0x8ab6a0 | vtbl_pvehicle_SubPhysicsObject | Shared physics sub-object |
| 0x008add1c | inline RTTI list | pvehicle subclass + component-key list |

`FECarRecord` has no static vtable — access via `FEPlayerCarDB::GetCarRecordByHandle @ 0x56ecc0` and use the FECarRecord:: methods (`GetType @ 0x5816b0`, `GetCost @ 0x581730`, …).

---

## 4. Event / message hashes

Hashes are bStringHash32 (Jenkins mix3, seed `0xABCDEF00`). Use `bStringHash @ 0x460bf0` to verify any extra ones.

| Hash | Identifier | Use |
|------|-----------|-----|
| 0x8AB83EDB | FEngTypes::Type1 | FE message channel 1 |
| 0x9D73BC15 | FEngTypes::Type2 | FE message channel 2 |
| 0x5230FAF6 | FEngTypes::Type3 | FE message channel 3 |
| 0xA19BB14C | FEngTypes::Type4 | FE message channel 4 |
| 0x821E6378 | FEngTypes::Type5 | FE message channel 5 |
| 0x609F6B15 | IconDisplayTypes::ShowIcon | World-icon visibility on |
| 0x5079c8f8 | STATE_HIDDEN | wave-12 hash, icon/object hidden |
| 0x033113ac | STATE_VISIBLE | wave-12 hash, object visible |
| 0x0016a259 | STATE_IDLE | wave-12 hash, idle state |
| 0xA6B47FAC | bChunk("BASE") | Reference hash from project_bchunk_hash |

**Pursuit / cop event names** (broadcast via hashed channel; the names go through `bStringHash`):

| Name | Use |
|------|-----|
| `MPursuitBreaker` | Breaker activation message |
| `MBreakerStopCops` | Stop cops after breaker hits |
| `PursuitBreaker` | Generic breaker event |
| `PursuitBountyAwarded` | Heat awarded after pursuit ends |
| `PursuitStarted` | Initial-chase entry |
| `PursuitEnded` | Cooldown / Evaded / Busted |
| `MilestoneProgress` | Career milestone advance |
| `MSG_R_BI_DATACRC` | Save-integrity CRC check |
| `CAREER_DATA` | Career payload root |

Hash any of the above with `bStringHash @ 0x460bf0` or `stringhash32 @ 0x5cc240` to get the runtime u32.

---

## 5. Function-name addresses (top 50)

Most-used callable APIs. `__thiscall` first arg = `this`. `__cdecl` is plain push-args.

| Address | CC | Signature |
|---------|----|-----------|
| 0x454640 | __cdecl | `uint32 StringToKey(const char*)` |
| 0x460bf0 | __cdecl | `uint32 bStringHash(const char*)` |
| 0x5cc240 | __cdecl | `uint32 stringhash32(const char*)` |
| 0x455fd0 | __cdecl | `Collection* FindCollection(class_key, coll_key)` |
| 0x455bc0 | __thiscall | `Class* Database::GetClass(u32 key)` |
| 0x455960 | __thiscall | `Collection* Class::GetCollection(u32 key)` |
| 0x457380 | __thiscall | `Definition* Class::GetDefinition(u32 key)` |
| 0x4573c0 | __thiscall | `u32 Class::GetNextDefinition(u32)` |
| 0x451670 | __thiscall | `u32 Class::GetFirstDefinition()` |
| 0x451660 | __thiscall | `u32 Class::GetNumDefinitions()` |
| 0x453fc0 | __thiscall | `u32 Class::GetNumCollections()` |
| 0x456b00 | __thiscall | `u32 Class::GetFirstCollection()` |
| 0x456b20 | __thiscall | `u32 Class::GetNextCollection(u32)` |
| 0x454190 | __thiscall | `T* Collection::GetData(u32, int32)` |
| 0x4e4ea0 | __thiscall | `pvehicle* pvehicle::TryGetInstance(pvehicle&, u32, bool, bool)` |
| 0x422480 | __thiscall | `void AIVehicle::SetGoal(const UCrc32&)` |
| 0x443270 | __cdecl | `Sim::IActivity* AIPursuit::Construct(AIParams, UCrc32)` |
| 0x418000 | __thiscall | `void AITarget::Construct(ISimable*)` |
| 0x423750 | __thiscall | `void AITarget::Register(ISimable*)` |
| 0x423860 | __thiscall | `void AITarget::Acquire(ISimable*)` |
| 0x409e60 | __thiscall | `void AITarget::Clear()` |
| 0x6895a0 | __cdecl | `ISimable* Smackable::Construct(SmackableParams, UCrc32)` |
| 0x689820 | __cdecl | `IResetable* ResetCar::Construct(BehaviorParams)` |
| 0x612660 | __cdecl | `void SetWorldHeat(float)` |
| 0x612220 | __cdecl | `void AwardPlayerBounty(int32)` |
| 0x6123b0 | __cdecl | `void ForceAIControl(bool)` |
| 0x612420 | __cdecl | `void ClearAIControl(bool)` |
| 0x604f40 | __cdecl | `void SetCopsEnabled(bool)` |
| 0x60aac0 | __cdecl | `void ForcePursuitStart()` |
| 0x62ace0 | __cdecl | `void ForcePursuitBail()` |
| 0x62b110 | __cdecl | `void ShakeCamera()` |
| 0x60ab30 | __cdecl | `void BlowEngine(ISimable*)` |
| 0x60ab60 | __cdecl | `void SabotageEngine(ISimable*, float)` |
| 0x60deb0 | __cdecl | `void AbandonRace()` |
| 0x6050f0 | __cdecl | `void ShowPauseMenu()` |
| 0x605250 | __cdecl | `void JumpToCarLot()` |
| 0x6052b0 | __cdecl | `void JumpToSafehouse()` |
| 0x605360 | __cdecl | `void NavigatePlayerTo(GRuntimeInstance*, GTrigger*, float, bool)` |
| 0x42c830 | __cdecl | `void EngageGPS(UMath::Vector3*, float)` |
| 0x41ace0 | __cdecl | `void DisengageGPS()` |
| 0x5dbf00 | __cdecl | `void GRaceStatus::DisableBarriers()` |
| 0x5ea010 | __thiscall | `void GManager::UnspawnAllIcons()` |
| 0x5ede20 | __thiscall | `void GManager::SpawnAllLoadedSectionIcons()` |
| 0x5e5970 | __thiscall | `GIcon::GIcon(Type, Vector3&, float)` |
| 0x5ec270 | __thiscall | `void GIcon::Spawn()` |
| 0x5e5a00 | __thiscall | `void GIcon::Unspawn()` |
| 0x5ea0f0 | __thiscall | `void GIcon::SnapToGround()` |
| 0x56ecc0 | __thiscall | `FECarRecord* FEPlayerCarDB::GetCarRecordByHandle(u32)` |
| 0x56ecf0 | __thiscall | `FECarRecord* FEPlayerCarDB::GetCarByIndex(u32)` |
| 0x56f0c0 | __thiscall | `void FEPlayerCarDB::AwardBonusCars()` |
| 0x5a41e0 | __thiscall | `void FEPlayerCarDB::AwardRivalCar(Attrib::StringKey)` |
| 0x739c70 | __thiscall | `CarPart* RideInfo::GetPart(CarSlotId)` |
| 0x759470 | __thiscall | `void RideInfo::SetUpgradePart(CarSlotId, eCareerUpgradeLevels)` |
| 0x7594a0 | __thiscall | `void RideInfo::SetStockParts()` |
| 0x75b220 | __thiscall | `void RideInfo::SetRandomParts()` |
| 0x759800 | __thiscall | `void RideInfo::SetRandomPaint()` |
| 0x667340 | __cdecl | `void BeginGameFlowUnloadTrack()` |
| 0x677fe0 | __cdecl | `bool Package::CanInstallJunkman(pvehicle&, Type)` |
| 0x678150 | __cdecl | `void Package::SetJunkman(pvehicle&, Type)` |
| 0x67c220 | __cdecl | `void Package::RemoveJunkman(pvehicle&, Type)` |
| 0x678ad0 | __cdecl | `void Package::SetLevel(pvehicle&, Type)` |
| 0x67f950 | __cdecl | `void Package::SetMaximum(pvehicle&)` |

---

## 6. Attribute name to hash (top 50)

Most-used physics + race + audio keys from `attribute_cracks_verified.json` (294 total). Crack with `StringToKey @ 0x454640`.

### Physics + chassis

| Name | Hash |
|------|------|
| MASS | 0x4A56503D |
| STEERING | 0xFEF5CC35 |
| TOP_SPEED (SpeedHighway) | 0x9E404E33 |
| SpeedStreet | 0x7C44962F |
| FOV | 0x263E9452 |
| Power | 0x96E40580 |
| TopBreak | 0xB4985085 |
| BrMultiply | 0x555FD699 |
| BmMultiply | 0xC8BAF5D6 |
| HEIGHT | 0x762B7718 |
| Width | 0x5816C1FC |
| TILTING | 0x665F4D74 |
| YAW_CONTROL | 0x64C43C4B |
| YAW_SPEED | 0xC2094707 |
| STIFFNESS | 0x7F8EEA1A |
| LATOFFSET | 0x2FC5F041 |
| MaxRPM | 0xA4D878EF |
| MinRPM | 0x3AC8B868 |
| Life | 0x81625B35 |
| Radius | 0x39BF8002 |
| InheritVelocity | 0x0099CB26 |
| MAX_NEWTONS | 0x0013821F |
| explosionForceLimit | 0x259021B6 |
| forceMultiplier | 0x3A5970F4 |
| damageMultiplier | 0xA6F789CB |
| triggerThreshold | 0xA6F45864 |
| DETACH_FORCE | 0xBE71DBAD |
| RESPAWN_TIME | 0x5F84F834 |
| ChargeTime | 0x4A985286 |

### Race / event

| Name | Hash |
|------|------|
| CarID | 0x0C35B607 |
| CarType | 0xF833C06F |
| RaceLength | 0x7C11C52E |
| RaceScoring | 0xD52754DA |
| TimeLimit | 0x7585F041 |
| TargetGold | 0x728E43FF |
| TargetSilver | 0x51CE16B7 |
| TargetBronze | 0x00DF8EB4 |
| CashReward | 0xAB0179F4 |
| IntroNIS | 0xDEC18D3E |
| OutroNIS | 0x54932966 |
| IsBoss | 0x79C5D68D |
| BossRace | 0xFF5EE5D6 |
| CopsInRace | 0x3918E889 |
| MaxHeatLevel | 0xF5A03629 |
| UseWorldHeat | 0x45F2AD6C |
| RacerName | 0xBEAB64C5 |
| RandomOpponent | 0x6DF0ABFE |
| RollingStart | 0xB809D19C |
| HandlingRating | 0xAACBE2E7 |
| PresetRide | 0x416A8409 |
| eDRIVE_BY_TYPE | 0xDB9D3A16 |
| Region | 0xCB01E454 |
| StartTime | 0x839602AB |

---

## 7. DirectInput scan codes (DIK_*)

NFSMW reads DInput DIK_ codes (NOT virtual keys). These are the keys the binding registry uses.

| DIK_ | Hex | Key |
|------|-----|-----|
| DIK_ESCAPE | 0x01 | Esc |
| DIK_1 | 0x02 | 1 |
| DIK_2 | 0x03 | 2 |
| DIK_3 | 0x04 | 3 |
| DIK_4 | 0x05 | 4 |
| DIK_5 | 0x06 | 5 |
| DIK_TAB | 0x0F | Tab |
| DIK_Q | 0x10 | Q |
| DIK_W | 0x11 | W |
| DIK_E | 0x12 | E |
| DIK_R | 0x13 | R |
| DIK_T | 0x14 | T |
| DIK_RETURN | 0x1C | Enter |
| DIK_LCONTROL | 0x1D | LCtrl |
| DIK_A | 0x1E | A |
| DIK_S | 0x1F | S |
| DIK_D | 0x20 | D |
| DIK_F | 0x21 | F |
| DIK_LSHIFT | 0x2A | LShift |
| DIK_Z | 0x2C | Z |
| DIK_X | 0x2D | X |
| DIK_C | 0x2E | C |
| DIK_V | 0x2F | V |
| DIK_B | 0x30 | B |
| DIK_N | 0x31 | N |
| DIK_SPACE | 0x39 | Space |
| DIK_F1 | 0x3B | F1 |
| DIK_F2 | 0x3C | F2 |
| DIK_F3 | 0x3D | F3 |
| DIK_F4 | 0x3E | F4 |
| DIK_F5 | 0x3F | F5 |
| DIK_NUMPAD0 | 0x52 | Numpad 0 |
| DIK_RCONTROL | 0x9D | RCtrl |
| DIK_RSHIFT | 0x36 | RShift |
| DIK_UP | 0xC8 | UpArrow |
| DIK_LEFT | 0xCB | LeftArrow |
| DIK_RIGHT | 0xCD | RightArrow |
| DIK_DOWN | 0xD0 | DownArrow |

Resolve symbolic → action via `LookupUIInputBindingByCode @ 0x56ecc0`.

---

## 8. Race mode enum values

From `RaceType` enum (`Types/cFrontendDatabase.h`) and `RaceTypes` (`Types/RaceParameters.h`).

### RaceType (race_rules / FE)

| Value | Name |
|-------|------|
| 0 | Point2Point |
| 1 | Circuit |
| 2 | Drag |
| 3 | Knockout |
| 4 | Tollbooth |
| 5 | SpeedTrap |
| 6 | Checkpoint |
| 7 | CashGrab |
| 8 | Challenge |
| 9 | JumpToSpeedTrap |
| 10 | JumpToMilestone |
| 0xFFFFFFFF | None |

### RaceTypes (RaceParameters)

| Value | Name |
|-------|------|
| 0 | None |
| 1 | SingleRace |
| 2 | TimeTrial |
| 3 | LapKnockout |
| 4 | RaceKnockout (typo: `RaceRnockout`) |
| 5 | Tournament |
| 6 | CarShow |
| 7 | GetAway |

### eFEGameModes (bitfield)

| Bit | Value | Mode |
|-----|-------|------|
| - | 0 | None |
| 0 | 0x00001 | Career |
| 1 | 0x00002 | Challenge |
| 2 | 0x00004 | QuickRace |
| 3 | 0x00008 | Online |
| 4 | 0x00010 | Options |
| 5 | 0x00020 | Customize |
| 6 | 0x00040 | Lan |
| 7 | 0x00080 | ProfileManager |
| 8 | 0x00100 | CareerManager |
| 9 | 0x00200 | RapSheet |
| 10 | 0x00400 | ModeSelect |
| 11 | 0x00800 | Trailers |
| 15 | 0x08000 | CarLot |
| 16 | 0x10000 | Safehouse |
| 17 | 0x20000 | PostRival |
| 18 | 0x40000 | BeatGame |

### ePursuitStatus

| Value | Name |
|-------|------|
| 0 | InitialChase |
| 1 | BackupRequested |
| 2 | Cooldown |
| 3 | Busted |
| 4 | Evaded |

### DriverClass

| Value | Name |
|-------|------|
| 0 | Human |
| 1 | Traffic |
| 2 | Cop |
| 3 | Racer |
| 4 | None |
| 5 | NIS |
| 6 | Remote |

---

## 9. State + status hashes (wave-12)

Object-state hashes the engine compares against `o[+0x??]` fields. Crack via `StringToKey`.

| Hash | State |
|------|-------|
| 0x5079c8f8 | HIDDEN |
| 0x033113ac | VISIBLE |
| 0x0016a259 | IDLE |
| 0x609f6b15 | ShowIcon (`IconDisplayTypes::ShowIcon`) |
| 0x8AB83EDB | FEng::Type1 |
| 0x9D73BC15 | FEng::Type2 |
| 0x5230FAF6 | FEng::Type3 |
| 0xA19BB14C | FEng::Type4 |
| 0x821E6378 | FEng::Type5 |

### RigidBody::Status (bitflags)

| Bit | Hex | Name |
|-----|-----|------|
| 0 | 0x0001 | NoTrigger |
| 1 | 0x0002 | Attached |
| 2 | 0x0004 | CollisionWorld |
| 3 | 0x0008 | CollisionObject |
| 5 | 0x0020 | EnableDrag |
| 6 | 0x0040 | CheckWorld |
| 7 | 0x0080 | FixedCG |
| 8 | 0x0100 | Animating |
| 9 | 0x0200 | Initialized |
| 10 | 0x0400 | Integrating |
| 11 | 0x0800 | EnableDragAngular |
| 12 | 0x1000 | DisableIntegrator |
| 13 | 0x2000 | ModifyPrims |
| 14 | 0x4000 | Inactive |
| 15 | 0x8000 | CollisionGround |

### GCharacter::State

| Value | Name |
|-------|------|
| 0 | Invalid |
| 1 | Unspawned |
| 2 | SpawningWaitingForModel |
| 3 | SpawningWaitingForTrack |
| 4 | Spawned |
| 5 | UnspawningWaitingUntilOffscreen |

### GIcon::Flags (bitfield)

| Bit | Hex | Flag |
|-----|-----|------|
| 0 | 0x01 | ShowInWorld |
| 1 | 0x02 | ShowOnMap |
| 2 | 0x04 | Spawned |
| 3 | 0x08 | Enabled |
| 4 | 0x10 | Disposable |
| 5 | 0x20 | SnappedToGround |
| 6 | 0x40 | ShowOnSpawn |
| 7 | 0x80 | GPSing |

### TriggerFlags (bitfield, `Types.h`)

| Bit | Hex | Flag |
|-----|-----|------|
| 0 | 0x00001 | Enabled |
| 1 | 0x00002 | OneShot |
| 2 | 0x00004 | PlayerActivated |
| 3 | 0x00008 | AIActivated |
| 4 | 0x00010 | ExplosionActivated |
| 5 | 0x00020 | VehicleActivated |
| 13 | 0x02000 | PlayerCharActivated |
| 15 | 0x08000 | FireOnExit |
| 17 | 0x20000 | CopActivated |
| 18 | 0x40000 | FireOnEntry |

---

## See also

- `docs/sdk_addrs.json` — full 181-entry SDK index
- `docs/attribute_cracks_verified.json` — 294 cracked attribute names
- `docs/sdk_enums.json` — 65 enums in machine-readable form
- `MEMORY.md` topics: `project_attribute_schema`, `project_script_natives`, `project_cop_ai_pursuit`, `project_career_milestones`, `project_bchunk_hash`
