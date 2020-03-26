INCLUDE(FindPkgConfig)
PKG_CHECK_MODULES(PC_TACMAC tacmac)

FIND_PATH(
    TACMAC_INCLUDE_DIRS
    NAMES tacmac/api.h
    HINTS $ENV{TACMAC_DIR}/include
        ${PC_TACMAC_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    TACMAC_LIBRARIES
    NAMES gnuradio-tacmac
    HINTS $ENV{TACMAC_DIR}/lib
        ${PC_TACMAC_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/tacmacTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(TACMAC DEFAULT_MSG TACMAC_LIBRARIES TACMAC_INCLUDE_DIRS)
MARK_AS_ADVANCED(TACMAC_LIBRARIES TACMAC_INCLUDE_DIRS)
