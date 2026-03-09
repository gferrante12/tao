// Do NOT change. Changes will be lost next time file is generated

#define R__DICTIONARY_FILENAME dItmpdIbdIjunodOihepdOacdOcndIel9_amd64_gcc11dIReleasedIJ25dO7dO1dItaoswdIbuilddIDataModeldICalibEventdIsrcdITvtCalibEvtDict
#define R__NO_DEPRECATION

/*******************************************************************/
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define G__DICTIONARY
#include "ROOT/RConfig.hxx"
#include "TClass.h"
#include "TDictAttributeMap.h"
#include "TInterpreter.h"
#include "TROOT.h"
#include "TBuffer.h"
#include "TMemberInspector.h"
#include "TInterpreter.h"
#include "TVirtualMutex.h"
#include "TError.h"

#ifndef G__ROOT
#define G__ROOT
#endif

#include "RtypesImp.h"
#include "TIsAProxy.h"
#include "TFileMergeInfo.h"
#include <algorithm>
#include "TCollectionProxyInfo.h"
/*******************************************************************/

#include "TDataMember.h"

// Header files passed as explicit arguments
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/Event/TvtCalibEvt.h"

// Header files passed via #pragma extra_include

// The generated code does not explicitly qualify STL entities
namespace std {} using namespace std;

namespace ROOT {
   static void *new_TaocLcLTvtCalibEvt(void *p = nullptr);
   static void *newArray_TaocLcLTvtCalibEvt(Long_t size, void *p);
   static void delete_TaocLcLTvtCalibEvt(void *p);
   static void deleteArray_TaocLcLTvtCalibEvt(void *p);
   static void destruct_TaocLcLTvtCalibEvt(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const ::Tao::TvtCalibEvt*)
   {
      ::Tao::TvtCalibEvt *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TInstrumentedIsAProxy< ::Tao::TvtCalibEvt >(nullptr);
      static ::ROOT::TGenericClassInfo 
         instance("Tao::TvtCalibEvt", ::Tao::TvtCalibEvt::Class_Version(), "Event/TvtCalibEvt.h", 9,
                  typeid(::Tao::TvtCalibEvt), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &::Tao::TvtCalibEvt::Dictionary, isa_proxy, 4,
                  sizeof(::Tao::TvtCalibEvt) );
      instance.SetNew(&new_TaocLcLTvtCalibEvt);
      instance.SetNewArray(&newArray_TaocLcLTvtCalibEvt);
      instance.SetDelete(&delete_TaocLcLTvtCalibEvt);
      instance.SetDeleteArray(&deleteArray_TaocLcLTvtCalibEvt);
      instance.SetDestructor(&destruct_TaocLcLTvtCalibEvt);
      return &instance;
   }
   TGenericClassInfo *GenerateInitInstance(const ::Tao::TvtCalibEvt*)
   {
      return GenerateInitInstanceLocal(static_cast<::Tao::TvtCalibEvt*>(nullptr));
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const ::Tao::TvtCalibEvt*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));
} // end of namespace ROOT

namespace Tao {
//______________________________________________________________________________
atomic_TClass_ptr TvtCalibEvt::fgIsA(nullptr);  // static to hold class pointer

//______________________________________________________________________________
const char *TvtCalibEvt::Class_Name()
{
   return "Tao::TvtCalibEvt";
}

//______________________________________________________________________________
const char *TvtCalibEvt::ImplFileName()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::TvtCalibEvt*)nullptr)->GetImplFileName();
}

//______________________________________________________________________________
int TvtCalibEvt::ImplFileLine()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::TvtCalibEvt*)nullptr)->GetImplFileLine();
}

//______________________________________________________________________________
TClass *TvtCalibEvt::Dictionary()
{
   fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::TvtCalibEvt*)nullptr)->GetClass();
   return fgIsA;
}

//______________________________________________________________________________
TClass *TvtCalibEvt::Class()
{
   if (!fgIsA.load()) { R__LOCKGUARD(gInterpreterMutex); fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::TvtCalibEvt*)nullptr)->GetClass(); }
   return fgIsA;
}

} // namespace Tao
namespace Tao {
//______________________________________________________________________________
void TvtCalibEvt::Streamer(TBuffer &R__b)
{
   // Stream an object of class Tao::TvtCalibEvt.

   if (R__b.IsReading()) {
      R__b.ReadClassBuffer(Tao::TvtCalibEvt::Class(),this);
   } else {
      R__b.WriteClassBuffer(Tao::TvtCalibEvt::Class(),this);
   }
}

} // namespace Tao
namespace ROOT {
   // Wrappers around operator new
   static void *new_TaocLcLTvtCalibEvt(void *p) {
      return  p ? new(p) ::Tao::TvtCalibEvt : new ::Tao::TvtCalibEvt;
   }
   static void *newArray_TaocLcLTvtCalibEvt(Long_t nElements, void *p) {
      return p ? new(p) ::Tao::TvtCalibEvt[nElements] : new ::Tao::TvtCalibEvt[nElements];
   }
   // Wrapper around operator delete
   static void delete_TaocLcLTvtCalibEvt(void *p) {
      delete (static_cast<::Tao::TvtCalibEvt*>(p));
   }
   static void deleteArray_TaocLcLTvtCalibEvt(void *p) {
      delete [] (static_cast<::Tao::TvtCalibEvt*>(p));
   }
   static void destruct_TaocLcLTvtCalibEvt(void *p) {
      typedef ::Tao::TvtCalibEvt current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class ::Tao::TvtCalibEvt

namespace ROOT {
   static TClass *vectorlETaocLcLTvtCalibChannelgR_Dictionary();
   static void vectorlETaocLcLTvtCalibChannelgR_TClassManip(TClass*);
   static void *new_vectorlETaocLcLTvtCalibChannelgR(void *p = nullptr);
   static void *newArray_vectorlETaocLcLTvtCalibChannelgR(Long_t size, void *p);
   static void delete_vectorlETaocLcLTvtCalibChannelgR(void *p);
   static void deleteArray_vectorlETaocLcLTvtCalibChannelgR(void *p);
   static void destruct_vectorlETaocLcLTvtCalibChannelgR(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const vector<Tao::TvtCalibChannel>*)
   {
      vector<Tao::TvtCalibChannel> *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TIsAProxy(typeid(vector<Tao::TvtCalibChannel>));
      static ::ROOT::TGenericClassInfo 
         instance("vector<Tao::TvtCalibChannel>", -2, "vector", 389,
                  typeid(vector<Tao::TvtCalibChannel>), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &vectorlETaocLcLTvtCalibChannelgR_Dictionary, isa_proxy, 0,
                  sizeof(vector<Tao::TvtCalibChannel>) );
      instance.SetNew(&new_vectorlETaocLcLTvtCalibChannelgR);
      instance.SetNewArray(&newArray_vectorlETaocLcLTvtCalibChannelgR);
      instance.SetDelete(&delete_vectorlETaocLcLTvtCalibChannelgR);
      instance.SetDeleteArray(&deleteArray_vectorlETaocLcLTvtCalibChannelgR);
      instance.SetDestructor(&destruct_vectorlETaocLcLTvtCalibChannelgR);
      instance.AdoptCollectionProxyInfo(TCollectionProxyInfo::Generate(TCollectionProxyInfo::Pushback< vector<Tao::TvtCalibChannel> >()));

      instance.AdoptAlternate(::ROOT::AddClassAlternate("vector<Tao::TvtCalibChannel>","std::vector<Tao::TvtCalibChannel, std::allocator<Tao::TvtCalibChannel> >"));
      return &instance;
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const vector<Tao::TvtCalibChannel>*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));

   // Dictionary for non-ClassDef classes
   static TClass *vectorlETaocLcLTvtCalibChannelgR_Dictionary() {
      TClass* theClass =::ROOT::GenerateInitInstanceLocal(static_cast<const vector<Tao::TvtCalibChannel>*>(nullptr))->GetClass();
      vectorlETaocLcLTvtCalibChannelgR_TClassManip(theClass);
   return theClass;
   }

   static void vectorlETaocLcLTvtCalibChannelgR_TClassManip(TClass* ){
   }

} // end of namespace ROOT

namespace ROOT {
   // Wrappers around operator new
   static void *new_vectorlETaocLcLTvtCalibChannelgR(void *p) {
      return  p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::TvtCalibChannel> : new vector<Tao::TvtCalibChannel>;
   }
   static void *newArray_vectorlETaocLcLTvtCalibChannelgR(Long_t nElements, void *p) {
      return p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::TvtCalibChannel>[nElements] : new vector<Tao::TvtCalibChannel>[nElements];
   }
   // Wrapper around operator delete
   static void delete_vectorlETaocLcLTvtCalibChannelgR(void *p) {
      delete (static_cast<vector<Tao::TvtCalibChannel>*>(p));
   }
   static void deleteArray_vectorlETaocLcLTvtCalibChannelgR(void *p) {
      delete [] (static_cast<vector<Tao::TvtCalibChannel>*>(p));
   }
   static void destruct_vectorlETaocLcLTvtCalibChannelgR(void *p) {
      typedef vector<Tao::TvtCalibChannel> current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class vector<Tao::TvtCalibChannel>

namespace {
  void TriggerDictionaryInitialization_TvtCalibEvtDict_Impl() {
    static const char* headers[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/Event/TvtCalibEvt.h",
nullptr
    };
    static const char* includePaths[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Python/3.11.10/include/python3.11",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Boost/1.85.0",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/log4cpp/1.1.3/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/ROOT/6.30.08/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J24.2.0/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Geant4/10.04.p02.juno/include/geant4",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/HepMC/2.06.11/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/genie/3.04.02/include/GENIE",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/frontier/2.10.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-c/6.1.9/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-cpp/1.1.12/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libyaml/0.2.4/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime/core/session",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/nuwro/21.09.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/CalibEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.4.0/ExternalLibs/ROOT/6.30.08/include/",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/CalibEvent/",
nullptr
    };
    static const char* fwdDeclCode = R"DICTFWDDCLS(
#line 1 "TvtCalibEvtDict dictionary forward declarations' payload"
#pragma clang diagnostic ignored "-Wkeyword-compat"
#pragma clang diagnostic ignored "-Wignored-attributes"
#pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
extern int __Cling_AutoLoading_Map;
namespace Tao{class __attribute__((annotate("$clingAutoload$/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/Event/TvtCalibEvt.h")))  TvtCalibEvt;}
)DICTFWDDCLS";
    static const char* payloadCode = R"DICTPAYLOAD(
#line 1 "TvtCalibEvtDict dictionary payload"


#define _BACKWARD_BACKWARD_WARNING_H
// Inline headers
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/Event/TvtCalibEvt.h"

#undef  _BACKWARD_BACKWARD_WARNING_H
)DICTPAYLOAD";
    static const char* classesHeaders[] = {
"Tao::TvtCalibEvt", payloadCode, "@",
nullptr
};
    static bool isInitialized = false;
    if (!isInitialized) {
      TROOT::RegisterModule("TvtCalibEvtDict",
        headers, includePaths, payloadCode, fwdDeclCode,
        TriggerDictionaryInitialization_TvtCalibEvtDict_Impl, {}, classesHeaders, /*hasCxxModule*/false);
      isInitialized = true;
    }
  }
  static struct DictInit {
    DictInit() {
      TriggerDictionaryInitialization_TvtCalibEvtDict_Impl();
    }
  } __TheDictionaryInitializer;
}
void TriggerDictionaryInitialization_TvtCalibEvtDict() {
  TriggerDictionaryInitialization_TvtCalibEvtDict_Impl();
}
