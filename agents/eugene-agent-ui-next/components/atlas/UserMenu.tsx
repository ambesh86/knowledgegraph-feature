"use client";

import { useRouter } from "next/navigation";
import {
  Avatar,
  Box,
  HStack,
  Menu,
  MenuButton,
  MenuDivider,
  MenuItem,
  MenuList,
  Text,
  VStack,
} from "@chakra-ui/react";
import { LuLogOut, LuSettings, LuUser } from "react-icons/lu";
import { useAuth, type AtlasUser } from "@/lib/atlas/useAuth";

function initials(name: string): string {
  return name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
}

export function UserMenu({ user }: { user: AtlasUser }) {
  const router = useRouter();
  const { logout } = useAuth();

  async function onLogout() {
    await logout();
    router.push("/login");
    router.refresh();
  }

  return (
    <Menu placement="bottom-end" autoSelect={false}>
      <MenuButton>
        <HStack spacing={2} pl={1} pr={2} py={1} borderRadius="9px" _hover={{ bg: "bg.hover" }}>
          <Avatar size="sm" name={user.name} getInitials={() => initials(user.name)}
            bg="iris.500" color="white" boxSize="30px" fontSize="12px" fontWeight={700} />
          <Text fontSize="14px" fontWeight={600} display={{ base: "none", lg: "block" }}
            color="text.primary">
            {user.name.split(" ")[0]}
          </Text>
        </HStack>
      </MenuButton>
      <MenuList bg="bg.panel" borderColor="border.default" boxShadow="pop" borderRadius="12px"
        py={2} minW="220px">
        <Box px={3} py={2}>
          <VStack align="flex-start" spacing={0}>
            <Text fontSize="14px" fontWeight={600} color="text.primary">{user.name}</Text>
            <Text fontSize="12px" color="text.muted">{user.email}</Text>
          </VStack>
        </Box>
        <MenuDivider borderColor="border.subtle" />
        <MenuItem icon={<LuUser size={15} />} bg="bg.panel" _hover={{ bg: "bg.hover" }}
          fontSize="14px" color="text.secondary" onClick={() => router.push("/settings")}>
          Profile
        </MenuItem>
        <MenuItem icon={<LuSettings size={15} />} bg="bg.panel" _hover={{ bg: "bg.hover" }}
          fontSize="14px" color="text.secondary" onClick={() => router.push("/settings")}>
          Settings
        </MenuItem>
        <MenuDivider borderColor="border.subtle" />
        <MenuItem icon={<LuLogOut size={15} />} bg="bg.panel" _hover={{ bg: "bg.hover" }}
          fontSize="14px" color="brand.500" onClick={onLogout}>
          Sign out
        </MenuItem>
      </MenuList>
    </Menu>
  );
}
